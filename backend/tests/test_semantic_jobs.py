import threading
from collections.abc import Iterator
from dataclasses import replace
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import semantic as semantic_api
from app.db.session import Base, get_db
from app.models import KeywordGroup, Paper, PaperFeature, ScoringWeights
from app.models.semantic import (
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SEMANTIC_WEIGHT,
    SemanticSettings,
)
from app.services import semantic_index, semantic_jobs
from app.services.scoring import load_scoring_context, rescore_all_papers
from app.services.semantic_runtime import MODEL_DIMENSION, SemanticModelError


@pytest.fixture(autouse=True)
def isolated_job_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semantic_jobs, "_job_lock", threading.Lock())
    monkeypatch.setattr(semantic_jobs, "_job", {
        "status": "idle", "error": None, "processed_papers": 0, "total_papers": 0,
    })


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(bind=engine, autoflush=False) as db:
        db.add_all([SemanticSettings(), ScoringWeights()])
        db.commit()
        yield db
    engine.dispose()


@pytest.fixture()
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(semantic_api.router, prefix="/settings")

    def request_db():
        yield db_session

    app.dependency_overrides[get_db] = request_db
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": True, "model_cached": True,
    })
    with TestClient(app) as test_client:
        yield test_client


def seed_paper(db: Session) -> int:
    db.add(KeywordGroup(
        name="Robotics", description="Flexible robot control",
        positive_keywords=["tendon-driven robot"],
    ))
    item = Paper(
        title="Continuum manipulator control", normalized_title="continuum manipulator control",
        abstract="Flexible motion in confined spaces", source="arxiv", published_date=date.today(),
    )
    db.add(item)
    db.flush()
    db.add(PaperFeature(paper_id=item.id, final_score=87, classification="Highly Relevant"))
    db.commit()
    return item.id


@pytest.mark.parametrize(
    ("installed", "cached", "expected"),
    [(False, False, "missing_dependency"), (True, False, "missing_model"), (True, True, "ready")],
)
def test_semantic_get_reports_dependency_and_model_readiness_without_loading(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
    installed: bool, cached: bool, expected: str,
) -> None:
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": installed, "model_cached": cached,
    })

    response = client.get("/settings/semantic")

    assert response.status_code == 200
    body = response.json()
    assert body["runtime_status"] == expected
    assert body["model_ready"] is (installed and cached)
    assert body["dependencies_ready"] is installed
    assert body["is_enabled"] is True
    assert body["min_similarity"] == DEFAULT_MIN_SIMILARITY
    assert body["semantic_weight"] == DEFAULT_SEMANTIC_WEIGHT


@pytest.mark.parametrize("path", ["prepare", "reindex"])
def test_semantic_actions_return_clear_conflict_when_dependencies_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str,
) -> None:
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": False, "model_cached": False,
    })

    response = client.post(f"/settings/semantic/{path}")

    assert response.status_code == 409
    assert response.json()["detail"]


def test_reindex_requires_prepared_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": True, "model_cached": False,
    })

    response = client.post("/settings/semantic/reindex")

    assert response.status_code == 409
    assert "模型" in response.json()["detail"]


@pytest.mark.parametrize(("path", "expected_kwargs"), [("prepare", {"prepare": True}),
                                                        ("reindex", {})])
def test_semantic_actions_schedule_without_passing_request_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str, expected_kwargs: dict,
) -> None:
    scheduled = []
    monkeypatch.setattr(
        semantic_api, "start_semantic_job", lambda **kwargs: scheduled.append(kwargs),
    )

    response = client.post(f"/settings/semantic/{path}")

    assert response.status_code == 202
    assert scheduled == [expected_kwargs]


@pytest.mark.parametrize("payload", [
    {"is_enabled": None}, {"min_similarity": None}, {"semantic_weight": None},
    {"min_similarity": 0.49}, {"min_similarity": 0.99},
    {"semantic_weight": -0.01}, {"semantic_weight": 1.01},
    {"min_similarity": "nan"}, {"semantic_weight": "Infinity"},
])
def test_semantic_settings_validate_null_ranges_and_finite_values(
    client: TestClient, payload: dict,
) -> None:
    assert client.put("/settings/semantic", json=payload).status_code == 422


def test_disabling_semantics_immediately_restores_rules_without_background_job(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_paper(db_session)
    scheduled = []
    monkeypatch.setattr(
        semantic_api, "start_semantic_job", lambda **kwargs: scheduled.append(kwargs),
    )

    response = client.put("/settings/semantic", json={"is_enabled": False})

    assert response.status_code == 200
    assert response.json()["is_enabled"] is False
    db_session.expire_all()
    feature = db_session.query(PaperFeature).one()
    assert feature.final_score == 0
    assert feature.semantic_details["status"] == "disabled"
    assert scheduled == []


def test_semantic_put_commits_before_scheduling_and_preserves_omitted_fields(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled = []
    committed = []

    def record_commit(session):
        committed.append(True)

    event.listen(db_session, "after_commit", record_commit)

    def schedule(**kwargs):
        assert committed
        scheduled.append(kwargs)
        return True

    monkeypatch.setattr(semantic_api, "start_semantic_job", schedule)
    response = client.put("/settings/semantic", json={"min_similarity": 0.85})

    assert response.status_code == 200
    assert response.json()["min_similarity"] == 0.85
    assert response.json()["semantic_weight"] == DEFAULT_SEMANTIC_WEIGHT
    assert scheduled == [{}]


class PerfectRuntime:
    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (MODEL_DIMENSION - 1) for _ in texts]

    def encode_passages(self, texts: list[str]) -> list[list[float]]:
        return self.encode_queries(texts)


@pytest.mark.parametrize("change", ["required_keywords", "is_enabled"])
def test_job_reloads_concurrent_settings_in_fresh_locked_scoring_session(
    tmp_path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'semantics.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        db.add_all([SemanticSettings(), ScoringWeights()])
        seed_paper(db)
    monkeypatch.setattr(semantic_index, "get_runtime", lambda: PerfectRuntime())
    inference_sessions = []
    scoring_sessions = []
    statements = []
    real_prepare = semantic_index.prepare_semantic_context

    def record_statement(conn, cursor, statement, params, context, many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)

    def prepare_and_mutate(db, context, papers, **kwargs):
        inference_sessions.append(db)
        if len(inference_sessions) == 1:
            assert context.groups[0].required_keywords == []
            with factory() as other_db:
                if change == "required_keywords":
                    other_db.query(KeywordGroup).one().required_keywords = ["missing-required"]
                else:
                    other_db.query(SemanticSettings).one().is_enabled = False
                other_db.commit()
        return real_prepare(db, context, papers, **kwargs)

    def rescore_current_settings(db, **kwargs):
        scoring_sessions.append(db)
        context = load_scoring_context(db)
        if change == "required_keywords":
            assert context.groups[0].required_keywords == ["missing-required"]
        else:
            assert context.semantic.enabled is False
        return rescore_all_papers(db, **kwargs)

    monkeypatch.setattr(semantic_jobs, "prepare_semantic_context", prepare_and_mutate)
    monkeypatch.setattr(semantic_jobs, "rescore_all_papers", rescore_current_settings)

    semantic_jobs._run_semantic_job(prepare=False, session_factory=factory)

    assert semantic_jobs._job["status"] == "completed"
    assert inference_sessions and scoring_sessions
    assert all(
        score is not inference for score in scoring_sessions for inference in inference_sessions
    )
    assert any(statement.upper() == "BEGIN IMMEDIATE" for statement in statements)
    with factory() as db:
        assert db.query(PaperFeature).one().final_score == 0
    engine.dispose()


@pytest.mark.parametrize("fail_on", ["prepare", "inference"])
def test_failed_semantic_job_reports_failure_without_overwriting_existing_scores(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, fail_on: str,
) -> None:
    seed_paper(db_session)
    factory = sessionmaker(bind=db_session.get_bind(), autoflush=False)

    class BrokenRuntime:
        def prepare_model(self):
            raise SemanticModelError("Model preparation failed")

    def fail_index(db, context, papers, **kwargs):
        return replace(context, semantic=replace(context.semantic, error="Inference failed"))

    monkeypatch.setattr(semantic_jobs, "get_runtime", lambda: BrokenRuntime())
    monkeypatch.setattr(semantic_jobs, "prepare_semantic_context", fail_index)

    semantic_jobs._run_semantic_job(prepare=fail_on == "prepare", session_factory=factory)

    assert semantic_jobs._job["status"] == "failed"
    assert semantic_jobs._job["error"]
    db_session.expire_all()
    assert db_session.query(PaperFeature).one().final_score == 87


def test_duplicate_job_requests_do_not_start_concurrent_workers(monkeypatch: pytest.MonkeyPatch):
    threads = []

    class ControlledThread:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.started = False
            threads.append(self)

        def start(self):
            self.started = True

    monkeypatch.setattr(semantic_jobs.threading, "Thread", ControlledThread)
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": True, "model_cached": True,
    })
    def session_factory():
        pytest.fail("Controlled worker should not execute")

    assert semantic_jobs.start_semantic_job(session_factory=session_factory) is True
    assert semantic_jobs.start_semantic_job(session_factory=session_factory) is False
    assert semantic_jobs.start_semantic_job(prepare=True, session_factory=session_factory) is False
    assert len(threads) == 1
    assert threads[0].started is True
    assert threads[0].kwargs["kwargs"]["session_factory"] is session_factory


@pytest.mark.parametrize(("installed", "cached"), [(False, False), (True, False)])
def test_index_job_does_not_start_without_ready_model(
    monkeypatch: pytest.MonkeyPatch, installed: bool, cached: bool,
) -> None:
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": installed, "model_cached": cached,
    })

    assert semantic_jobs.start_semantic_job() is False
    assert semantic_jobs._job["status"] == "idle"


def test_new_settings_after_final_commit_are_reindexed_before_job_completes(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'completion-window.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        db.add_all([SemanticSettings(), ScoringWeights()])
        seed_paper(db)
    monkeypatch.setattr(semantic_index, "get_runtime", lambda: PerfectRuntime())
    monkeypatch.setattr(semantic_jobs, "model_status", lambda: {
        "dependencies_installed": True, "model_cached": True,
    })
    requested = []
    inference_sessions = []

    def request_after_commit(session):
        if requested:
            return
        assert semantic_jobs._job["status"] == "indexing"
        with factory() as other_db:
            other_db.query(KeywordGroup).one().required_keywords = ["new-required-term"]
            other_db.commit()
        requested.append(semantic_jobs.start_semantic_job(session_factory=factory))

    def rescore_and_request_after_commit(db, **kwargs):
        result = rescore_all_papers(db, **kwargs)
        event.listen(db, "after_commit", request_after_commit, once=True)
        return result

    def record_inference(db, context, papers, **kwargs):
        inference_sessions.append(db)
        return semantic_index.prepare_semantic_context(db, context, papers, **kwargs)

    monkeypatch.setattr(semantic_jobs, "rescore_all_papers", rescore_and_request_after_commit)
    monkeypatch.setattr(semantic_jobs, "prepare_semantic_context", record_inference)

    semantic_jobs._run_semantic_job(prepare=False, session_factory=factory)

    assert requested == [False]
    assert len(inference_sessions) == 2
    assert semantic_jobs._job["status"] == "completed"
    with factory() as db:
        assert db.query(PaperFeature).one().final_score == 0
        assert semantic_jobs.needs_semantic_index(db) is False
    engine.dispose()

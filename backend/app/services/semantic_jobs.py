import threading
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.paper import Paper, PaperFeature
from app.models.semantic import (
    DEFAULT_MIN_SIMILARITY,
    DEFAULT_SEMANTIC_WEIGHT,
    SemanticEmbedding,
    SemanticSettings,
)
from app.services.scoring import load_scoring_context, rescore_all_papers
from app.services.semantic_index import MODEL_KEY, prepare_semantic_context, semantic_index_key
from app.services.semantic_runtime import MODEL_ID, SemanticRuntimeError, get_runtime, model_status
from app.services.semantic_types import paper_text, text_hash

_job_lock = threading.Lock()
_job: dict[str, object] = {
    "status": "idle",
    "error": None,
    "processed_papers": 0,
    "total_papers": 0,
}


def _update_job(**values: object) -> None:
    with _job_lock:
        _job.update(values)


def semantic_status(db: Session) -> dict[str, object]:
    config = db.query(SemanticSettings).first()
    runtime = model_status()
    installed = bool(runtime["dependencies_installed"])
    cached = bool(runtime["model_cached"])
    with _job_lock:
        job = dict(_job)
    return {
        "is_enabled": config.is_enabled if config else True,
        "min_similarity": config.min_similarity if config else DEFAULT_MIN_SIMILARITY,
        "semantic_weight": config.semantic_weight if config else DEFAULT_SEMANTIC_WEIGHT,
        "model_name": MODEL_ID,
        "model_ready": installed and cached,
        "dependencies_ready": installed,
        "runtime_status": "missing_dependency"
        if not installed
        else "missing_model"
        if not cached
        else "ready",
        "cached_papers": db.query(PaperFeature.paper_id)
        .join(
            SemanticEmbedding,
            (
                SemanticEmbedding.content_hash
                == PaperFeature.semantic_details["content_hash"].as_string()
            ),
        )
        .filter(
            SemanticEmbedding.model_key == MODEL_KEY,
            SemanticEmbedding.kind == "passage",
        )
        .count(),
        **job,
    }


def needs_semantic_index(db: Session) -> bool:
    context = load_scoring_context(db)
    if not context.semantic.enabled:
        return False
    index_key = semantic_index_key(context)
    rows = (
        db.query(Paper, PaperFeature)
        .outerjoin(
            PaperFeature,
            PaperFeature.paper_id == Paper.id,
        )
        .all()
    )
    return any(
        not feature
        or not feature.semantic_details
        or feature.semantic_details.get("index_key") != index_key
        or feature.semantic_details.get("content_hash") != text_hash(paper_text(paper))
        or not feature.semantic_details.get("index_complete")
        for paper, feature in rows
    )


def schedule_semantic_completion(db: Session) -> bool:
    runtime = model_status()
    if not runtime["dependencies_installed"] or not runtime["model_cached"]:
        return False
    return start_semantic_job() if needs_semantic_index(db) else False


def start_semantic_job(
    *,
    prepare: bool = False,
    session_factory: Callable[[], Session] | None = None,
) -> bool:
    if not prepare:
        runtime = model_status()
        if not runtime["dependencies_installed"] or not runtime["model_cached"]:
            return False
    with _job_lock:
        if _job["status"] in {"preparing", "indexing"}:
            # A settings commit can arrive after the final DB commit but before
            # this worker publishes completion. Remember it instead of dropping
            # the request while the task still appears busy.
            _job["rerun_requested"] = True
            return False
        _job.update(
            status="preparing" if prepare else "indexing",
            error=None,
            processed_papers=0,
            total_papers=0,
            rerun_requested=False,
        )
    threading.Thread(
        target=_run_semantic_job,
        kwargs={"prepare": prepare, "session_factory": session_factory or SessionLocal},
        name="paper-radar-semantic",
        daemon=True,
    ).start()
    return True


def _run_semantic_job(*, prepare: bool, session_factory: Callable[[], Session]) -> None:
    try:
        if prepare:
            get_runtime().prepare_model()
        _update_job(status="indexing")
        # Embeddings are content addressed. A changed configuration cannot
        # invalidate old cache rows, and scoring always reloads the latest data.
        for _attempt in range(3):
            with session_factory() as db:
                context = load_scoring_context(db)
                papers = db.query(Paper).order_by(Paper.id).all()
                prepared = prepare_semantic_context(
                    db,
                    context,
                    papers,
                    progress=lambda done, total: _update_job(
                        processed_papers=done,
                        total_papers=total,
                    ),
                )
                db.commit()
                if prepared.semantic.enabled and prepared.semantic.error:
                    raise SemanticRuntimeError(prepared.semantic.error)

            # Use a fresh session and a short write transaction AFTER inference.
            # SQLite's immediate lock prevents a newer settings/feedback commit
            # from slipping between our final reads and score writes.
            with session_factory() as db:
                if db.get_bind().dialect.name == "sqlite":
                    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                else:
                    db.connection(execution_options={"isolation_level": "SERIALIZABLE"})
                rescore_all_papers(db, compute_semantics=False)
                incomplete = needs_semantic_index(db)
                db.commit()
            if not incomplete:
                with _job_lock:
                    if _job.pop("rerun_requested", False):
                        continue
                    _job.update(
                        status="completed",
                        error=None,
                        processed_papers=len(papers),
                        total_papers=len(papers),
                    )
                    return
        raise SemanticRuntimeError("研究方向在重算期间发生变化，请重新执行语义重算。")
    except Exception as exc:  # noqa: BLE001
        _update_job(status="failed", error=str(exc))

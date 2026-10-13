from collections.abc import Iterator
from dataclasses import asdict, replace
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import KeywordGroup, Paper, ScoringWeights, SourceConfig
from app.models.semantic import SemanticEmbedding, SemanticSettings
from app.services import semantic_index
from app.services.scoring import calculate_paper_score, load_scoring_context
from app.services.semantic_index import prepare_semantic_context
from app.services.semantic_runtime import MODEL_DIMENSION, SemanticModelError
from app.services.semantic_types import group_anchor_text, group_text, paper_text, text_hash


def unit_vector(index: int = 0) -> list[float]:
    return [float(position == index) for position in range(MODEL_DIMENSION)]


class FakeRuntime:
    """Deterministic vectors exercise indexing without a model or network."""

    def __init__(self) -> None:
        self.queries: list[list[str]] = []
        self.passages: list[list[str]] = []
        self.fail_on: str | None = None
        self.passage_axis = 0
        self.query_axes: dict[str, int] = {}

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        self.queries.append(list(texts))
        if self.fail_on == "query":
            raise SemanticModelError("The local model is unavailable.")
        return [unit_vector(self.query_axes.get(text, 0)) for text in texts]

    def encode_passages(self, texts: list[str]) -> list[list[float]]:
        self.passages.append(list(texts))
        if self.fail_on == "passage":
            raise SemanticModelError("The local model is unavailable.")
        return [unit_vector(self.passage_axis) for _ in texts]


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(bind=engine, autoflush=False) as db:
        yield db
    engine.dispose()


@pytest.fixture()
def runtime(monkeypatch: pytest.MonkeyPatch) -> FakeRuntime:
    fake = FakeRuntime()
    monkeypatch.setattr(semantic_index, "get_runtime", lambda: fake)
    return fake


def seed_context(db: Session, **group_overrides):
    group = KeywordGroup(**({
        "name": "柔性机器人",
        "description": "研究柔性机械臂的形状控制和运动规划",
        "positive_keywords": ["tendon-driven robot"],
        "is_enabled": True,
    } | group_overrides))
    db.add_all([group, ScoringWeights(), SemanticSettings(is_enabled=True)])
    db.flush()
    return load_scoring_context(db)


def paper(index: int = 0, **overrides) -> Paper:
    return Paper(**({
        "title": f"Continuum manipulator shape control {index}",
        "normalized_title": f"continuum manipulator shape control {index}",
        "abstract": "A flexible manipulator performs dexterous motion in confined spaces.",
        "source": "arxiv",
        "published_date": date.today(),
    } | overrides))


def rules_only(context):
    return replace(context, semantic=replace(context.semantic, enabled=False))


def scoring_values(score):
    values = asdict(score)
    values.pop("semantic_details")
    return values


def test_semantic_only_match_enters_recommendations_without_fabricated_keyword_hits(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    item = paper()
    assert calculate_paper_score(item, rules_only(context)).final_score == 0

    prepared = prepare_semantic_context(db_session, context, [item])
    result = calculate_paper_score(item, prepared)

    assert result.final_score >= 60
    assert result.classification in {"Worth Checking", "Highly Relevant"}
    assert result.matched_groups == ["柔性机器人"]
    assert result.matched_positive == []
    assert result.semantic_details["match_type"] == "semantic"
    assert result.semantic_details["group"] == "柔性机器人"
    assert result.semantic_details["similarity"] == 1
    assert result.semantic_details["status"] == "applied"
    assert runtime.queries == [[
        group_text(context.groups[0]), group_anchor_text(context.groups[0]),
    ]]
    assert runtime.passages == [[paper_text(item)]]


def test_semantic_match_cannot_bypass_missing_required_keyword(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session, required_keywords=["surgical"])
    item = paper()
    prepared = prepare_semantic_context(db_session, context, [item])

    result = calculate_paper_score(item, prepared)

    assert prepared.semantic.matches[text_hash(paper_text(item))]
    assert result.final_score == 0
    assert result.matched_groups == []
    assert result.matched_positive == []
    assert result.semantic_details["match_type"] == "none"


def test_required_keyword_still_allows_semantic_recovery_without_primary_keyword(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session, required_keywords=["surgical"])
    item = paper(title="Surgical continuum manipulator")
    prepared = prepare_semantic_context(db_session, context, [item])

    assert calculate_paper_score(item, prepared).final_score >= 60


def test_optional_keyword_only_match_can_be_promoted_by_semantics(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session, optional_keywords=["shape control"])
    item = paper()
    lexical = calculate_paper_score(item, rules_only(context))
    prepared = prepare_semantic_context(db_session, context, [item])
    result = calculate_paper_score(item, prepared)

    assert lexical.final_score <= 35
    assert result.final_score >= 60
    assert result.matched_positive == ["shape control"]
    assert result.semantic_details["match_type"] == "hybrid"
    assert result.semantic_details["lexical_topic_score"] == lexical.topic_score


@pytest.mark.parametrize("fail_on", ["query", "passage"])
def test_model_failure_preserves_all_rule_scoring_values(
    db_session: Session, runtime: FakeRuntime, fail_on: str,
) -> None:
    context = seed_context(db_session, negative_keywords=["surgical"])
    item = paper(title="Tendon-driven robot for surgical intervention")
    expected = calculate_paper_score(item, rules_only(context))
    runtime.fail_on = fail_on

    prepared = prepare_semantic_context(db_session, context, [item])
    actual = calculate_paper_score(item, prepared)

    assert scoring_values(actual) == scoring_values(expected)
    assert prepared.semantic.status == "unavailable"
    assert "unavailable" in prepared.semantic.error
    assert actual.semantic_details["status"] == "unavailable"


def test_below_threshold_semantics_preserve_rules_without_creating_match(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    runtime.passage_axis = 1
    item = paper()
    prepared = prepare_semantic_context(db_session, context, [item])
    result = calculate_paper_score(item, prepared)

    assert prepared.semantic.matches[text_hash(paper_text(item))]
    assert result.final_score == 0
    assert result.matched_groups == []
    assert result.semantic_details["match_type"] == "none"


def test_disabled_semantics_return_exact_rule_result_and_do_not_encode(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    item = paper()
    prepared = prepare_semantic_context(db_session, context, [item])
    assert calculate_paper_score(item, prepared).final_score >= 60
    query_calls = list(runtime.queries)
    passage_calls = list(runtime.passages)
    disabled = rules_only(prepared)

    returned = prepare_semantic_context(db_session, disabled, [item])
    result = calculate_paper_score(item, returned)

    assert scoring_values(result) == scoring_values(
        calculate_paper_score(item, rules_only(context))
    )
    assert result.semantic_details["status"] == "disabled"
    assert result.semantic_details["match_type"] == "none"
    assert runtime.queries == query_calls
    assert runtime.passages == passage_calls


def test_unranked_source_remains_zero_even_for_perfect_semantic_match(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    db_session.add(SourceConfig(
        source_name="arxiv", display_name="arXiv", participates_in_ranking=False,
    ))
    db_session.flush()
    context = load_scoring_context(db_session)
    item = paper()
    prepared = prepare_semantic_context(db_session, context, [item])

    result = calculate_paper_score(item, prepared)

    assert result.topic_score > 0
    assert result.final_score == 0
    assert result.classification == "Filtered"


def test_content_cache_reuses_vectors_across_sessions_without_encoding(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    items = [paper(), paper(1)]
    first = prepare_semantic_context(db_session, context, items)
    db_session.commit()
    assert db_session.query(SemanticEmbedding).count() == 4

    with Session(bind=db_session.get_bind()) as reopened:
        second = prepare_semantic_context(reopened, load_scoring_context(reopened), items)

    assert first.semantic.matches == second.semantic.matches
    assert first.semantic.complete == second.semantic.complete
    assert len(runtime.queries) == 1
    assert len(runtime.passages) == 1


def test_paper_content_change_encodes_only_changed_passage(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    items = [paper(), paper(1)]
    prepare_semantic_context(db_session, context, items)
    old_hash = text_hash(paper_text(items[0]))
    items[0].abstract = "New work on collision-free motion of soft manipulators."

    prepared = prepare_semantic_context(db_session, context, items)

    assert text_hash(paper_text(items[0])) != old_hash
    assert runtime.passages[-1] == [paper_text(items[0])]
    assert len(runtime.passages) == 2
    assert len(runtime.queries) == 1
    assert len(prepared.semantic.complete) == 2


def test_research_description_change_encodes_profile_but_reuses_paper_vectors(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    item = paper()
    first = prepare_semantic_context(db_session, context, [item])
    old_hash = text_hash(group_text(context.groups[0]))
    context.groups[0].description = "研究柔性机器人的动态避障和复杂环境中的运动规划"

    second = prepare_semantic_context(db_session, context, [item])

    assert text_hash(group_text(context.groups[0])) != old_hash
    assert second.semantic.index_key != first.semantic.index_key
    assert runtime.queries[-1] == [group_text(context.groups[0])]
    assert len(runtime.queries) == 2
    assert len(runtime.passages) == 1


def test_model_revision_key_change_invalidates_query_and_passage_vectors(
    db_session: Session, runtime: FakeRuntime, monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = seed_context(db_session)
    items = [paper(), paper(1)]
    first = prepare_semantic_context(db_session, context, items)
    monkeypatch.setattr(semantic_index, "MODEL_KEY", semantic_index.MODEL_KEY + ":new-revision")

    second = prepare_semantic_context(db_session, context, items)

    assert second.semantic.index_key != first.semantic.index_key
    assert len(runtime.queries) == 2
    assert len(runtime.passages) == 2
    assert db_session.query(SemanticEmbedding).count() == 8


def test_semantic_index_batches_passages_instead_of_encoding_each_paper(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    items = [paper(index) for index in range(37)]

    prepared = prepare_semantic_context(db_session, context, items)

    assert [len(batch) for batch in runtime.queries] == [2]
    assert [len(batch) for batch in runtime.passages] == [16, 16, 5]
    assert len(prepared.semantic.complete) == 37
    assert all(calculate_paper_score(item, prepared).final_score >= 60 for item in items)


def test_cache_only_scoring_does_not_request_runtime_when_vectors_are_missing(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = seed_context(db_session)
    item = paper(title="Tendon-driven robot kinematics")

    def unexpected_runtime():
        pytest.fail("Cache-only startup scoring must not load or download the model")

    monkeypatch.setattr(semantic_index, "get_runtime", unexpected_runtime)
    prepared = prepare_semantic_context(db_session, context, [item], compute_missing=False)

    assert scoring_values(calculate_paper_score(item, prepared)) == scoring_values(
        calculate_paper_score(item, rules_only(context))
    )
    assert prepared.semantic.status == "unavailable"
    assert db_session.query(SemanticEmbedding).count() == 0


def test_invalid_cached_vector_is_reencoded_and_repaired_without_duplicate_row(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    item = paper()
    db_session.add(SemanticEmbedding(
        model_key=semantic_index.MODEL_KEY,
        kind="passage",
        content_hash=text_hash(paper_text(item)),
        vector=[0.0],
    ))
    db_session.flush()

    prepared = prepare_semantic_context(db_session, context, [item])
    db_session.expire_all()

    repaired = db_session.query(SemanticEmbedding).filter_by(kind="passage").one()
    assert len(repaired.vector) == MODEL_DIMENSION
    assert repaired.vector == unit_vector()
    assert db_session.query(SemanticEmbedding).count() == 3
    assert prepared.semantic.status == "ready"
    assert runtime.passages == [[paper_text(item)]]


def test_broad_description_similarity_cannot_replace_core_topic_similarity(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    item = paper()
    runtime.query_axes[group_anchor_text(context.groups[0])] = 1

    prepared = prepare_semantic_context(db_session, context, [item])
    match = prepared.semantic.matches[text_hash(paper_text(item))][
        text_hash(group_text(context.groups[0]))
    ]

    assert match.profile_similarity == 1
    assert match.anchor_similarity == 0
    assert match.similarity == 0
    assert match.score == 0
    assert calculate_paper_score(item, prepared).final_score == 0


def test_empty_paper_text_does_not_block_semantics_for_other_papers_in_batch(
    db_session: Session, runtime: FakeRuntime,
) -> None:
    context = seed_context(db_session)
    valid = paper()
    empty = paper(1, title=" \t ", abstract="\n ")

    prepared = prepare_semantic_context(db_session, context, [valid, empty])

    assert prepared.semantic.status == "ready"
    assert prepared.semantic.error is None
    assert runtime.passages == [[paper_text(valid)]]
    assert text_hash("") in prepared.semantic.complete
    assert prepared.semantic.matches[text_hash("")] == {}
    assert calculate_paper_score(valid, prepared).final_score >= 60
    assert calculate_paper_score(empty, prepared).final_score == 0


def test_all_empty_papers_are_complete_without_loading_runtime(
    db_session: Session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = seed_context(db_session)
    items = [paper(title="", abstract=""), paper(1, title="\t", abstract=" \n")]

    def unexpected_runtime():
        pytest.fail("Empty passages need no inference")

    monkeypatch.setattr(semantic_index, "get_runtime", unexpected_runtime)
    prepared = prepare_semantic_context(db_session, context, items)

    assert prepared.semantic.status == "ready"
    assert prepared.semantic.complete == {text_hash("")}
    assert prepared.semantic.matches == {text_hash(""): {}}
    assert db_session.query(SemanticEmbedding).count() == 0

import json
import math
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.semantic import SemanticEmbedding
from app.services.semantic_runtime import (
    MODEL_DIMENSION,
    MODEL_ID,
    MODEL_REVISION,
    SemanticRuntimeError,
    get_runtime,
)
from app.services.semantic_types import (
    SemanticMatch,
    cosine_similarity,
    group_anchor_text,
    group_text,
    paper_text,
    similarity_to_score,
    text_hash,
)

if TYPE_CHECKING:
    from app.services.scoring import ScoringContext

MODEL_KEY = f"{MODEL_ID}@{MODEL_REVISION}:e5-prefix-mean-v1"
BATCH_SIZE = 16


def semantic_index_key(context: "ScoringContext") -> str:
    return text_hash(
        json.dumps(
            {
                "model": MODEL_KEY,
                "query_strategy": "profile-and-primary-v2",
                "profiles": sorted(
                    group_text(group)
                    for group in context.groups
                    if group.is_enabled is not False and group.priority_weight != 0
                ),
                "threshold": context.semantic.min_similarity,
                "weight": context.semantic.weight,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def _valid_vector(vector: object) -> bool:
    return (
        isinstance(vector, list)
        and len(vector) == MODEL_DIMENSION
        and all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector)
        and any(value != 0 for value in vector)
    )


def _cached_vectors(db: Session, kind: str, keys: list[str]) -> dict[str, list[float]]:
    cached = {}
    for start in range(0, len(keys), 200):
        rows = (
            db.query(SemanticEmbedding)
            .filter(
                SemanticEmbedding.model_key == MODEL_KEY,
                SemanticEmbedding.kind == kind,
                SemanticEmbedding.content_hash.in_(keys[start : start + 200]),
            )
            .all()
        )
        for row in rows:
            if _valid_vector(row.vector):
                cached[row.content_hash] = row.vector
    return cached


def _cache_vectors(db: Session, kind: str, vectors: dict[str, list[float]]) -> None:
    if not vectors:
        return
    rows = [
        {"model_key": MODEL_KEY, "kind": kind, "content_hash": key, "vector": vector}
        for key, vector in vectors.items()
    ]
    dialect = db.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    # Concurrent requests may encode the same content. An upsert also repairs
    # malformed/stale cache rows without rolling back the paper transaction.
    for start in range(0, len(rows), BATCH_SIZE):
        statement = insert(SemanticEmbedding).values(rows[start : start + BATCH_SIZE])
        db.execute(
            statement.on_conflict_do_update(
                index_elements=["model_key", "kind", "content_hash"],
                set_={"vector": statement.excluded.vector},
            )
        )


def prepare_semantic_context(
    db: Session,
    context: "ScoringContext",
    papers: list[Paper],
    *,
    compute_missing: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> "ScoringContext":
    if not context.semantic.enabled:
        return context
    profiles = {
        text_hash(profile): profile
        for group in context.groups
        if group.is_enabled is not False
        and group.priority_weight != 0
        and (profile := group_text(group))
    }
    anchors = {
        text_hash(group_text(group)): text_hash(group_anchor_text(group))
        for group in context.groups
        if group.is_enabled is not False and group.priority_weight != 0 and group_text(group)
    }
    profiles.update(
        {
            text_hash(group_anchor_text(group)): group_anchor_text(group)
            for group in context.groups
            if group.is_enabled is not False and group.priority_weight != 0 and group_text(group)
        }
    )
    all_passages = {text_hash(paper_text(paper)): paper_text(paper) for paper in papers}
    passages = {key: value for key, value in all_passages.items() if value}
    empty_passages = set(all_passages) - set(passages)
    query_vectors = _cached_vectors(db, "query", list(profiles))
    passage_vectors = _cached_vectors(db, "passage", list(passages))
    generated: dict[str, dict[str, list[float]]] = {"query": {}, "passage": {}}
    error = None
    if progress:
        progress(len(empty_passages) + len(passage_vectors), len(all_passages))

    if compute_missing and profiles and passages:
        try:
            runtime = get_runtime()
            for kind, texts, vectors, encode in [
                ("query", profiles, query_vectors, runtime.encode_queries),
                ("passage", passages, passage_vectors, runtime.encode_passages),
            ]:
                missing = [key for key in texts if key not in vectors]
                for start in range(0, len(missing), BATCH_SIZE):
                    keys = missing[start : start + BATCH_SIZE]
                    encoded = encode([texts[key] for key in keys])
                    if len(encoded) != len(keys) or not all(_valid_vector(v) for v in encoded):
                        raise ValueError("The local model returned invalid embeddings.")
                    for key, vector in zip(keys, encoded, strict=True):
                        vectors[key] = vector
                        generated[kind][key] = vector
                    if progress and kind == "passage":
                        progress(len(empty_passages) + len(passage_vectors), len(all_passages))
        except (SemanticRuntimeError, ValueError) as exc:
            error = str(exc)

    # Finish inference before the first cache INSERT takes a SQLite write lock.
    for kind, vectors in generated.items():
        _cache_vectors(db, kind, vectors)

    complete = set(empty_passages)
    matches: dict[str, dict[str, SemanticMatch]] = {key: {} for key in empty_passages}
    for key in passages:
        if not profiles:
            complete.add(key)
            matches[key] = {}
            continue
        if key not in passage_vectors:
            continue
        matches[key] = {}
        for profile_key, anchor_key in anchors.items():
            if profile_key not in query_vectors or anchor_key not in query_vectors:
                continue
            profile_similarity = cosine_similarity(query_vectors[profile_key], passage_vectors[key])
            anchor_similarity = cosine_similarity(query_vectors[anchor_key], passage_vectors[key])
            similarity = min(profile_similarity, anchor_similarity)
            matches[key][profile_key] = SemanticMatch(
                similarity=similarity,
                score=similarity_to_score(similarity, context.semantic.min_similarity),
                profile_similarity=profile_similarity,
                anchor_similarity=anchor_similarity,
            )
        if len(query_vectors) == len(profiles):
            complete.add(key)
    return replace(
        context,
        semantic=replace(
            context.semantic,
            model=MODEL_ID,
            status="ready" if len(complete) == len(all_passages) else "unavailable",
            error=error,
            index_key=semantic_index_key(context),
            complete=complete,
            matches=matches,
        ),
    )

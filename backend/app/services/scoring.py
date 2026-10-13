from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.keyword_group import KeywordGroup
from app.models.paper import Paper, PaperFeature
from app.models.scoring import (
    DEFAULT_SCORING_WEIGHTS,
    LEGACY_SCORING_WEIGHTS,
    SCORING_VERSION,
    ScoringWeights,
)
from app.models.semantic import DEFAULT_MIN_SIMILARITY, DEFAULT_SEMANTIC_WEIGHT, SemanticSettings
from app.models.source_config import SourceConfig
from app.services.keyword_matching import contains_keyword, normalize_text, unique_keywords
from app.services.semantic_types import (
    SemanticEvidence,
    SemanticMatch,
    group_text,
    paper_text,
    text_hash,
)

BASE_WEIGHT_FIELDS = ("topic_weight", "method_weight", "venue_weight", "freshness_weight")


@dataclass(frozen=True)
class ScoringContext:
    groups: tuple[KeywordGroup, ...]
    weights: ScoringWeights
    preferences: UserPreferences | None
    ranked_sources: dict[str, bool]
    semantic: SemanticEvidence = field(default_factory=SemanticEvidence)


@dataclass(frozen=True)
class ScoreBreakdown:
    matched_groups: list[str]
    matched_positive: list[str]
    matched_negative: list[str]
    topic_tags: list[str]
    method_tags: list[str]
    venue_score: float
    topic_score: float
    method_score: float
    freshness_score: float
    user_preference_score: float
    negative_filter_penalty: float
    final_score: float
    classification: str
    semantic_details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GroupEvidence:
    group: KeywordGroup
    topic_score: float
    positive_hits: list[str]
    negative_hits: list[str]
    lexical_topic_score: float = 0.0
    semantic_match: SemanticMatch | None = None


def classify_score(final_score: float) -> str:
    if final_score >= 80:
        return "Highly Relevant"
    if final_score >= 60:
        return "Worth Checking"
    if final_score >= 40:
        return "Low Priority"
    return "Filtered"


def load_scoring_context(db: Session) -> ScoringContext:
    groups = tuple(db.query(KeywordGroup).filter(KeywordGroup.is_enabled.is_(True)).all())
    weights = db.query(ScoringWeights).first() or ScoringWeights(**DEFAULT_SCORING_WEIGHTS)
    preferences = db.query(UserPreferences).first()
    ranked_sources = {
        source.source_name: source.participates_in_ranking
        for source in db.query(SourceConfig).all()
    }
    semantic = db.query(SemanticSettings).first()
    return ScoringContext(
        groups,
        weights,
        preferences,
        ranked_sources,
        SemanticEvidence(
            enabled=bool(semantic and semantic.is_enabled),
            min_similarity=semantic.min_similarity if semantic else DEFAULT_MIN_SIMILARITY,
            weight=semantic.semantic_weight if semantic else DEFAULT_SEMANTIC_WEIGHT,
            status="unavailable" if semantic and semantic.is_enabled else "disabled",
        ),
    )


def calculate_paper_score(paper: Paper, context: ScoringContext) -> ScoreBreakdown:
    title = normalize_text(paper.title or "")
    abstract = normalize_text(paper.abstract or "")
    text = f"{title}\n{abstract}"
    key = text_hash(paper_text(paper))
    semantic_matches = context.semantic.matches.get(key, {}) if context.semantic.enabled else {}
    evidence = []
    for group in context.groups:
        if group.is_enabled is False or group.priority_weight == 0:
            continue
        required = unique_keywords(group.required_keywords or [])
        if not all(
            contains_keyword(title, word) or contains_keyword(abstract, word) for word in required
        ):
            continue
        lexical = _group_evidence(group, title, abstract)
        semantic_match = semantic_matches.get(text_hash(group_text(group)))
        semantic_topic = (
            semantic_match.score * context.semantic.weight
            if context.semantic.enabled and semantic_match
            else 0.0
        )
        if lexical is None and semantic_topic == 0:
            continue
        lexical_topic = lexical.topic_score if lexical else 0.0
        negative_hits = (
            lexical.negative_hits
            if lexical
            else [
                word
                for word in unique_keywords(group.negative_keywords or [])
                if contains_keyword(title, word) or contains_keyword(abstract, word)
            ]
        )
        evidence.append(
            GroupEvidence(
                group=group,
                topic_score=max(lexical_topic, semantic_topic),
                positive_hits=lexical.positive_hits if lexical else [],
                negative_hits=negative_hits,
                lexical_topic_score=lexical_topic,
                semantic_match=semantic_match,
            )
        )
    method_tags = _method_tags(text)
    method_score = min(100.0, len(method_tags) * 25.0)
    venue_score = _venue_score(paper)
    freshness_score = _freshness_score(paper.published_date)
    normalized_weights = _normalized_base_weights(context.weights)

    # Evaluate each direction independently, including its exclusions and priority.
    # Adding a separate research interest cannot dilute an existing good match.
    candidates = []
    for match in evidence:
        preference_score = _user_preference_score(
            paper,
            text,
            [match.group.name],
            match.positive_hits,
            match.negative_hits,
            method_tags,
            context.preferences,
        )
        penalty = min(100.0, len(match.negative_hits) * 25.0)
        base_score = sum(
            score * weight
            for score, weight in zip(
                (match.topic_score, method_score, venue_score, freshness_score),
                normalized_weights,
                strict=True,
            )
        )
        priority = match.group.priority_weight
        base_score = min(match.topic_score, base_score * (1.0 if priority is None else priority))
        # A neutral preference contributes zero, rather than using up score capacity.
        adjusted = (
            base_score
            + (preference_score - 50.0) * 2 * _weight(context.weights, "user_preference_weight")
            - penalty * _weight(context.weights, "negative_filter_weight")
        )
        final = max(0.0, min(match.topic_score, adjusted))
        candidates.append((final, match, preference_score, penalty))

    best = max(
        candidates,
        key=lambda item: (item[0], item[1].topic_score, item[1].group.name),
        default=None,
    )
    final_score = round(best[0], 2) if best else 0.0
    if not context.ranked_sources.get(paper.source, True):
        final_score = 0.0
    winning = best[1] if best else None
    semantic_match = winning.semantic_match if winning else None
    lexical_topic = winning.lexical_topic_score if winning else 0.0
    semantic_boost = bool(
        semantic_match and semantic_match.score * context.semantic.weight > lexical_topic
    )
    details: dict[str, object] = {
        "status": (
            "disabled"
            if not context.semantic.enabled
            else "applied"
            if key in context.semantic.complete
            else "unavailable"
        ),
        "model": context.semantic.model,
        "group": winning.group.name if winning else None,
        "similarity": round(semantic_match.similarity, 6) if semantic_match else None,
        "profile_similarity": semantic_match.profile_similarity if semantic_match else None,
        "anchor_similarity": semantic_match.anchor_similarity if semantic_match else None,
        "semantic_score": round(semantic_match.score, 2) if semantic_match else 0.0,
        "lexical_topic_score": lexical_topic,
        "match_type": (
            "hybrid"
            if semantic_boost and lexical_topic > 0
            else "semantic"
            if semantic_boost
            else "lexical"
            if lexical_topic > 0
            else "none"
        ),
        "index_key": context.semantic.index_key,
        "content_hash": key,
        "index_complete": key in context.semantic.complete,
    }

    return ScoreBreakdown(
        matched_groups=sorted({match.group.name for match in evidence}),
        matched_positive=sorted(
            unique_keywords([keyword for match in evidence for keyword in match.positive_hits])
        ),
        matched_negative=sorted(best[1].negative_hits) if best else [],
        topic_tags=sorted({tag for match in evidence for tag in (match.group.related_tags or [])}),
        method_tags=method_tags,
        venue_score=venue_score,
        topic_score=best[1].topic_score if best else 0.0,
        method_score=method_score,
        freshness_score=freshness_score,
        user_preference_score=best[2] if best else 50.0,
        negative_filter_penalty=best[3] if best else 0.0,
        final_score=final_score,
        classification=classify_score(final_score),
        semantic_details=details,
    )


def _group_evidence(group: KeywordGroup, title: str, abstract: str) -> GroupEvidence | None:
    if group.is_enabled is False or group.priority_weight == 0:
        return None

    def matches(keyword: str) -> bool:
        # Do not accidentally form a phrase across the title/abstract boundary.
        return contains_keyword(title, keyword) or contains_keyword(abstract, keyword)

    required = unique_keywords(group.required_keywords or [])
    if not all(matches(keyword) for keyword in required):
        return None
    anchors = unique_keywords(group.positive_keywords or []) or required
    primary_hits = [keyword for keyword in anchors if matches(keyword)]
    anchor_keys = {normalize_text(keyword) for keyword in [*anchors, *required]}
    optional_hits = [
        keyword
        for keyword in unique_keywords(group.optional_keywords or [])
        if normalize_text(keyword) not in anchor_keys and matches(keyword)
    ]
    if not primary_hits and not optional_hits:
        return None

    if primary_hits:
        title_hit = any(contains_keyword(title, keyword) for keyword in primary_hits)
        topic_score = min(
            100.0,
            (90.0 if title_hit else 75.0)
            + min(10.0, (len(primary_hits) - 1) * 5.0)
            + min(10.0, len(optional_hits) * 5.0),
        )
    else:
        # Supporting terms alone do not establish the research topic.
        topic_score = min(35.0, len(optional_hits) * 10.0)
    return GroupEvidence(
        group=group,
        topic_score=topic_score,
        positive_hits=unique_keywords([*primary_hits, *optional_hits]),
        negative_hits=[
            keyword
            for keyword in unique_keywords(group.negative_keywords or [])
            if matches(keyword)
        ],
    )


def _weight(weights: ScoringWeights, name: str) -> float:
    value = getattr(weights, name)
    return DEFAULT_SCORING_WEIGHTS[name] if value is None else float(value)


def _normalized_base_weights(weights: ScoringWeights) -> tuple[float, ...]:
    values = tuple(_weight(weights, name) for name in BASE_WEIGHT_FIELDS)
    # Scale first so even large finite custom weights cannot overflow the sum.
    largest = max(values)
    if largest <= 0:
        return (0.0,) * len(values)
    scaled = tuple(value / largest for value in values)
    total = sum(scaled)
    return tuple(value / total for value in scaled)


def score_paper(
    db: Session,
    paper: Paper,
    context: ScoringContext | None = None,
    *,
    is_new: bool = False,
) -> PaperFeature:
    loaded_context = context or load_scoring_context(db)
    if context is None:
        from app.services.semantic_index import prepare_semantic_context

        loaded_context = prepare_semantic_context(db, loaded_context, [paper])
    feature = (
        None if is_new else db.query(PaperFeature).filter(PaperFeature.paper_id == paper.id).first()
    )
    if feature is None:
        feature = PaperFeature(paper_id=paper.id)
        db.add(feature)
    _apply_score(feature, calculate_paper_score(paper, loaded_context))
    if context is None:
        db.flush()
    return feature


def rescore_all_papers(
    db: Session,
    *,
    compute_semantics: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    db.flush()
    context = load_scoring_context(db)
    rows = (
        db.query(Paper, PaperFeature)
        .outerjoin(PaperFeature, PaperFeature.paper_id == Paper.id)
        .all()
    )
    from app.services.semantic_index import prepare_semantic_context

    context = prepare_semantic_context(
        db,
        context,
        [paper for paper, _ in rows],
        compute_missing=compute_semantics,
        progress=progress,
    )
    for paper, feature in rows:
        if feature is None:
            feature = PaperFeature(paper_id=paper.id)
            db.add(feature)
        _apply_score(feature, calculate_paper_score(paper, context))
    context.weights.algorithm_version = SCORING_VERSION
    db.add(context.weights)
    db.flush()


def upgrade_scoring(db: Session) -> None:
    """Upgrade defaults and cached scores together, preserving custom weight sets."""
    weights = db.query(ScoringWeights).first()
    if not weights or weights.algorithm_version >= SCORING_VERSION:
        return
    if all(getattr(weights, name) == value for name, value in LEGACY_SCORING_WEIGHTS.items()):
        for name, value in DEFAULT_SCORING_WEIGHTS.items():
            setattr(weights, name, value)
    # Startup must not load a model or perform inference before the desktop
    # launcher health deadline. Missing vectors are filled by a separate job.
    rescore_all_papers(db, compute_semantics=False)
    db.commit()


def _apply_score(feature: PaperFeature, score: ScoreBreakdown) -> None:
    feature.matched_keyword_groups = score.matched_groups
    feature.matched_positive_keywords = score.matched_positive
    feature.matched_negative_keywords = score.matched_negative
    feature.topic_tags = score.topic_tags
    feature.method_tags = score.method_tags
    feature.venue_score = score.venue_score
    feature.topic_score = score.topic_score
    feature.method_score = score.method_score
    feature.freshness_score = score.freshness_score
    feature.user_preference_score = score.user_preference_score
    feature.negative_filter_penalty = score.negative_filter_penalty
    feature.final_score = score.final_score
    feature.classification = score.classification
    feature.semantic_details = score.semantic_details


def _method_tags(text: str) -> list[str]:
    tags = []
    rules = {
        "user study": ["user study", "participants", "interview", "survey"],
        "systematic review": ["systematic review", "literature review", "meta-analysis"],
        "evaluation": ["evaluation", "benchmark", "experiment", "metrics"],
        "modeling": ["model", "simulation", "theoretical framework"],
        "graph-based": ["graph", "node-link", "network"],
        "human-ai collaboration": ["human-ai", "co-creation", "co-creative"],
    }
    for tag, keywords in rules.items():
        if any(contains_keyword(text, keyword) for keyword in keywords):
            tags.append(tag)
    return tags


def _venue_score(paper: Paper) -> float:
    # Names such as "Journal" are not quality evidence. Keep a neutral value
    # until an explicit venue-quality signal is available; venue preferences
    # are already handled by the personalization component.
    return 50.0


def _freshness_score(published_date: date | None) -> float:
    if not published_date:
        return 45.0
    age_days = max((date.today() - published_date).days, 0)
    if age_days <= 30:
        return 100.0
    if age_days <= 90:
        return 80.0
    if age_days <= 365:
        return 60.0
    return 35.0


def _user_preference_score(
    paper: Paper,
    text: str,
    matched_groups: list[str],
    matched_keywords: list[str],
    matched_negative_keywords: list[str],
    method_tags: list[str],
    preferences: UserPreferences | None,
) -> float:
    if not preferences:
        return 50.0
    keyword_weights = preferences.keyword_weights or {}
    venue_weights = preferences.venue_weights or {}
    method_weights = preferences.method_weights or {}
    topic_weights = preferences.topic_weights or {}
    negative_keyword_weights = preferences.negative_keyword_weights or {}
    score = 50.0
    for keyword in matched_keywords:
        score += float(keyword_weights.get(keyword, 0.0)) * 5
    for group in matched_groups:
        score += float(topic_weights.get(group, 0.0)) * 4
    for method in method_tags:
        score += float(method_weights.get(method, 0.0)) * 4
    if paper.venue:
        score += float(venue_weights.get(paper.venue, 0.0)) * 5
    negative_matches = set(matched_negative_keywords)
    negative_matches.update(
        keyword for keyword in negative_keyword_weights if contains_keyword(text, keyword)
    )
    for keyword in negative_matches:
        score -= float(negative_keyword_weights.get(keyword, 0.0)) * 5
    return max(0.0, min(100.0, score))

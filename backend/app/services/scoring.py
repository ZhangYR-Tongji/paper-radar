from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.keyword_group import KeywordGroup
from app.models.paper import Paper, PaperFeature
from app.models.scoring import ScoringWeights
from app.models.source_config import SourceConfig


@dataclass(frozen=True)
class ScoringContext:
    groups: tuple[KeywordGroup, ...]
    weights: ScoringWeights
    preferences: UserPreferences | None
    ranked_sources: dict[str, bool]


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
    weights = db.query(ScoringWeights).first() or ScoringWeights()
    preferences = db.query(UserPreferences).first()
    ranked_sources = {
        source.source_name: source.participates_in_ranking
        for source in db.query(SourceConfig).all()
    }
    return ScoringContext(groups, weights, preferences, ranked_sources)


def calculate_paper_score(paper: Paper, context: ScoringContext) -> ScoreBreakdown:
    groups = context.groups
    weights = context.weights
    preferences = context.preferences

    text = f"{paper.title} {paper.abstract}".casefold()
    matched_groups: list[str] = []
    matched_positive: list[str] = []
    matched_negative: list[str] = []
    topic_tags: list[str] = []

    weighted_positive_hits = 0.0
    possible_positive_hits = 0.0
    negative_hits = 0

    for group in groups:
        required_ok = all(_contains(text, keyword) for keyword in group.required_keywords)
        positive_hits = [keyword for keyword in group.positive_keywords if _contains(text, keyword)]
        optional_hits = [keyword for keyword in group.optional_keywords if _contains(text, keyword)]
        negative_group_hits = [
            keyword for keyword in group.negative_keywords if _contains(text, keyword)
        ]

        if required_ok and (positive_hits or optional_hits or not group.positive_keywords):
            matched_groups.append(group.name)
            topic_tags.extend(group.related_tags)
            matched_positive.extend(positive_hits + optional_hits)
            weighted_positive_hits += (
                len(positive_hits) + 0.5 * len(optional_hits)
            ) * group.priority_weight

        matched_negative.extend(negative_group_hits)
        negative_hits += len(negative_group_hits)
        possible_positive_hits += max(len(group.positive_keywords), 1) * group.priority_weight

    topic_score = min(
        100.0,
        (weighted_positive_hits / max(possible_positive_hits, 1.0)) * 100 * 2.5,
    )
    method_tags = _method_tags(text)
    method_score = min(100.0, len(method_tags) * 25.0)
    venue_score = _venue_score(paper)
    freshness_score = _freshness_score(paper.published_date)
    user_preference_score = _user_preference_score(
        paper,
        text,
        matched_groups,
        matched_positive,
        matched_negative,
        method_tags,
        preferences,
    )
    negative_filter_penalty = min(100.0, (negative_hits + len(matched_negative)) * 25.0)

    final_score = (
        topic_score * weights.topic_weight
        + method_score * weights.method_weight
        + venue_score * weights.venue_weight
        + freshness_score * weights.freshness_weight
        + user_preference_score * weights.user_preference_weight
        - negative_filter_penalty * weights.negative_filter_weight
    )
    final_score = max(0.0, min(100.0, final_score))
    if not context.ranked_sources.get(paper.source, True):
        final_score = 0.0

    return ScoreBreakdown(
        matched_groups=sorted(set(matched_groups)),
        matched_positive=sorted(set(matched_positive)),
        matched_negative=sorted(set(matched_negative)),
        topic_tags=sorted(set(topic_tags)),
        method_tags=method_tags,
        venue_score=venue_score,
        topic_score=topic_score,
        method_score=method_score,
        freshness_score=freshness_score,
        user_preference_score=user_preference_score,
        negative_filter_penalty=negative_filter_penalty,
        final_score=round(final_score, 2),
        classification=classify_score(final_score),
    )


def score_paper(
    db: Session,
    paper: Paper,
    context: ScoringContext | None = None,
    *,
    is_new: bool = False,
) -> PaperFeature:
    loaded_context = context or load_scoring_context(db)
    feature = (
        None
        if is_new
        else db.query(PaperFeature).filter(PaperFeature.paper_id == paper.id).first()
    )
    if feature is None:
        feature = PaperFeature(paper_id=paper.id)
        db.add(feature)
    _apply_score(feature, calculate_paper_score(paper, loaded_context))
    if context is None:
        db.flush()
    return feature


def rescore_all_papers(db: Session) -> None:
    db.flush()
    context = load_scoring_context(db)
    rows = (
        db.query(Paper, PaperFeature)
        .outerjoin(PaperFeature, PaperFeature.paper_id == Paper.id)
        .all()
    )
    for paper, feature in rows:
        if feature is None:
            feature = PaperFeature(paper_id=paper.id)
            db.add(feature)
        _apply_score(feature, calculate_paper_score(paper, context))
    db.flush()


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


def _contains(text: str, keyword: str) -> bool:
    return keyword.casefold() in text


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
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def _venue_score(paper: Paper) -> float:
    venue_text = " ".join(
        value for value in [paper.venue, paper.journal, paper.conference] if value
    ).casefold()
    if not venue_text:
        return 40.0
    medium_signal = ["arxiv", "conference", "journal", "transactions", "proceedings"]
    if any(item in venue_text for item in medium_signal):
        return 65.0
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
        keyword for keyword in negative_keyword_weights if _contains(text, keyword)
    )
    for keyword in negative_matches:
        score -= float(negative_keyword_weights.get(keyword, 0.0)) * 5
    return max(0.0, min(100.0, score))

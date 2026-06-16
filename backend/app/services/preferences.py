from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.paper import Paper, PaperFeature
from app.schemas.feedback import FeedbackUpsert

RATING_SIGNALS = {
    1: -1.0,
    2: -0.5,
    3: 0.25,
    4: 0.65,
    5: 1.0,
}
KEYWORD_STEP = 0.2
CONTEXT_STEP = 0.1


def update_user_preferences_after_feedback(
    db: Session,
    paper_id: int,
    feedback: FeedbackUpsert,
    previous_rating: int | None = None,
) -> bool:
    preferences = db.query(UserPreferences).first()
    if not preferences:
        preferences = UserPreferences()
        db.add(preferences)
        db.flush()

    paper = db.get(Paper, paper_id)
    feature = db.query(PaperFeature).filter(PaperFeature.paper_id == paper_id).first()
    if not paper or not feature:
        return False

    previous_signal = _rating_signal(previous_rating)
    next_signal = _rating_signal(feedback.rating)
    preference_delta = next_signal - previous_signal
    negative_delta = max(-next_signal, 0.0) - max(-previous_signal, 0.0)
    if preference_delta == 0 and negative_delta == 0:
        return False

    keyword_weights = dict(preferences.keyword_weights or {})
    venue_weights = dict(preferences.venue_weights or {})
    method_weights = dict(preferences.method_weights or {})
    topic_weights = dict(preferences.topic_weights or {})
    negative_keyword_weights = dict(preferences.negative_keyword_weights or {})

    for keyword in feature.matched_positive_keywords or []:
        _adjust_weight(keyword_weights, keyword, KEYWORD_STEP * preference_delta)
    for group in feature.matched_keyword_groups or []:
        _adjust_weight(topic_weights, group, CONTEXT_STEP * preference_delta)
    for method in feature.method_tags or []:
        _adjust_weight(method_weights, method, CONTEXT_STEP * preference_delta)
    if paper.venue:
        _adjust_weight(venue_weights, paper.venue, CONTEXT_STEP * preference_delta)
    for keyword in set((feature.matched_negative_keywords or []) + feedback.negative_feedback_tags):
        _adjust_weight(negative_keyword_weights, keyword, KEYWORD_STEP * negative_delta)

    preferences.keyword_weights = keyword_weights
    preferences.venue_weights = venue_weights
    preferences.method_weights = method_weights
    preferences.topic_weights = topic_weights
    preferences.negative_keyword_weights = negative_keyword_weights
    db.flush()
    return True


def _rating_signal(rating: int | None) -> float:
    if rating is None:
        return 0.0
    return RATING_SIGNALS.get(rating, 0.0)


def _adjust_weight(weights: dict[str, float], key: str, delta: float) -> None:
    if not key or delta == 0:
        return
    next_value = float(weights.get(key, 0.0)) + delta
    if abs(next_value) < 0.0001:
        weights.pop(key, None)
    else:
        weights[key] = round(next_value, 4)

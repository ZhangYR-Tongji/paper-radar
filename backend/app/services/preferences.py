from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.paper import Paper, PaperFeature
from app.schemas.feedback import FeedbackUpsert


def update_user_preferences_after_feedback(
    db: Session,
    paper_id: int,
    feedback: FeedbackUpsert,
) -> None:
    preferences = db.query(UserPreferences).first()
    if not preferences:
        preferences = UserPreferences()
        db.add(preferences)
        db.flush()

    paper = db.get(Paper, paper_id)
    feature = db.query(PaperFeature).filter(PaperFeature.paper_id == paper_id).first()
    if not paper or not feature or feedback.rating is None:
        return

    keyword_weights = dict(preferences.keyword_weights or {})
    venue_weights = dict(preferences.venue_weights or {})
    method_weights = dict(preferences.method_weights or {})
    topic_weights = dict(preferences.topic_weights or {})
    negative_keyword_weights = dict(preferences.negative_keyword_weights or {})

    if feedback.rating >= 5:
        for keyword in feature.matched_positive_keywords:
            keyword_weights[keyword] = keyword_weights.get(keyword, 0.0) + 0.2
        for group in feature.matched_keyword_groups:
            topic_weights[group] = topic_weights.get(group, 0.0) + 0.1
        for method in feature.method_tags:
            method_weights[method] = method_weights.get(method, 0.0) + 0.1
        if paper.venue:
            venue_weights[paper.venue] = venue_weights.get(paper.venue, 0.0) + 0.1
    elif feedback.rating <= 1:
        for keyword in feature.matched_positive_keywords:
            keyword_weights[keyword] = keyword_weights.get(keyword, 0.0) - 0.2
        for keyword in feature.matched_negative_keywords + feedback.negative_feedback_tags:
            negative_keyword_weights[keyword] = negative_keyword_weights.get(keyword, 0.0) + 0.2

    preferences.keyword_weights = keyword_weights
    preferences.venue_weights = venue_weights
    preferences.method_weights = method_weights
    preferences.topic_weights = topic_weights
    preferences.negative_keyword_weights = negative_keyword_weights
    db.flush()

from sqlalchemy import Column, Float, Integer

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin

DEFAULT_SCORING_WEIGHTS = {
    "topic_weight": 0.80,
    "method_weight": 0.05,
    "venue_weight": 0.0,
    "freshness_weight": 0.15,
    "user_preference_weight": 0.10,
    "negative_filter_weight": 0.20,
}
LEGACY_SCORING_WEIGHTS = {
    "topic_weight": 0.30,
    "method_weight": 0.20,
    "venue_weight": 0.15,
    "freshness_weight": 0.15,
    "user_preference_weight": 0.10,
    "negative_filter_weight": 0.10,
}
SCORING_VERSION = 2


class ScoringWeights(IdMixin, TimestampMixin, Base):
    __tablename__ = "scoring_weights"

    algorithm_version = Column(Integer, default=1, nullable=False)
    topic_weight = Column(Float, default=DEFAULT_SCORING_WEIGHTS["topic_weight"], nullable=False)
    method_weight = Column(Float, default=DEFAULT_SCORING_WEIGHTS["method_weight"], nullable=False)
    venue_weight = Column(Float, default=DEFAULT_SCORING_WEIGHTS["venue_weight"], nullable=False)
    freshness_weight = Column(
        Float, default=DEFAULT_SCORING_WEIGHTS["freshness_weight"], nullable=False
    )
    user_preference_weight = Column(
        Float, default=DEFAULT_SCORING_WEIGHTS["user_preference_weight"], nullable=False
    )
    negative_filter_weight = Column(
        Float, default=DEFAULT_SCORING_WEIGHTS["negative_filter_weight"], nullable=False
    )

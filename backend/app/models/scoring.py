from sqlalchemy import Column, Float

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class ScoringWeights(IdMixin, TimestampMixin, Base):
    __tablename__ = "scoring_weights"

    topic_weight = Column(Float, default=0.30, nullable=False)
    method_weight = Column(Float, default=0.20, nullable=False)
    venue_weight = Column(Float, default=0.15, nullable=False)
    freshness_weight = Column(Float, default=0.15, nullable=False)
    user_preference_weight = Column(Float, default=0.10, nullable=False)
    negative_filter_weight = Column(Float, default=0.10, nullable=False)

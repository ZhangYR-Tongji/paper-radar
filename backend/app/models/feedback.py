from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, Text

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class UserFeedback(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_feedback"

    paper_id = Column(Integer, ForeignKey("papers.id"), unique=True, index=True, nullable=False)
    rating = Column(Integer, nullable=True)
    positive_feedback_tags = Column(JSON, default=list, nullable=False)
    negative_feedback_tags = Column(JSON, default=list, nullable=False)
    is_saved = Column(Boolean, default=False, nullable=False)
    is_core = Column(Boolean, default=False, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    is_ignored = Column(Boolean, default=False, nullable=False)
    personal_note = Column(Text, default="", nullable=False)


class UserPreferences(IdMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    keyword_weights = Column(JSON, default=dict, nullable=False)
    venue_weights = Column(JSON, default=dict, nullable=False)
    method_weights = Column(JSON, default=dict, nullable=False)
    topic_weights = Column(JSON, default=dict, nullable=False)
    negative_keyword_weights = Column(JSON, default=dict, nullable=False)

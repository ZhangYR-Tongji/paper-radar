from sqlalchemy import JSON, Boolean, Column, Float, String, Text

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class KeywordGroup(IdMixin, TimestampMixin, Base):
    __tablename__ = "keyword_groups"

    name = Column(String(160), unique=True, index=True, nullable=False)
    description = Column(Text, default="", nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority_weight = Column(Float, default=1.0, nullable=False)
    positive_keywords = Column(JSON, default=list, nullable=False)
    negative_keywords = Column(JSON, default=list, nullable=False)
    required_keywords = Column(JSON, default=list, nullable=False)
    optional_keywords = Column(JSON, default=list, nullable=False)
    related_tags = Column(JSON, default=list, nullable=False)

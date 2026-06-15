from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class SourceConfig(IdMixin, TimestampMixin, Base):
    __tablename__ = "source_configs"

    source_name = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, default="", nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    daily_limit = Column(Integer, default=100, nullable=False)
    participates_in_ranking = Column(Boolean, default=True, nullable=False)
    metadata_only = Column(Boolean, default=True, nullable=False)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin


class FetchCursor(IdMixin, TimestampMixin, Base):
    __tablename__ = "fetch_cursors"
    __table_args__ = (
        UniqueConstraint("source_name", "keyword_group_id", name="uq_fetch_cursor_scope"),
    )

    source_name = Column(String(64), index=True, nullable=False)
    keyword_group_id = Column(Integer, ForeignKey("keyword_groups.id"), nullable=False)
    last_successful_until = Column(DateTime(timezone=True), nullable=True)
    last_run_id = Column(Integer, ForeignKey("fetch_runs.id"), nullable=True)
    last_status = Column(String(32), nullable=True)
    last_error_message = Column(Text, nullable=True)


class FetchRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "fetch_runs"

    trigger_type = Column(String(32), default="manual", nullable=False)
    status = Column(String(32), default="running", index=True, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    requested_from = Column(DateTime(timezone=True), nullable=True)
    requested_to = Column(DateTime(timezone=True), nullable=True)
    overlap_buffer_days = Column(Integer, default=3, nullable=False)
    enabled_sources = Column(JSON, default=list, nullable=False)
    enabled_keyword_groups = Column(JSON, default=list, nullable=False)
    total_raw_results = Column(Integer, default=0, nullable=False)
    total_new_papers = Column(Integer, default=0, nullable=False)
    total_duplicate_papers = Column(Integer, default=0, nullable=False)
    total_scored_papers = Column(Integer, default=0, nullable=False)
    total_highly_relevant = Column(Integer, default=0, nullable=False)
    total_low_priority = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)


class FetchRunItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "fetch_run_items"

    fetch_run_id = Column(Integer, ForeignKey("fetch_runs.id"), index=True, nullable=False)
    source_name = Column(String(64), index=True, nullable=False)
    keyword_group_id = Column(Integer, ForeignKey("keyword_groups.id"), nullable=False)
    fetch_from = Column(DateTime(timezone=True), nullable=True)
    fetch_to = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False)
    raw_result_count = Column(Integer, default=0, nullable=False)
    new_paper_count = Column(Integer, default=0, nullable=False)
    duplicate_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

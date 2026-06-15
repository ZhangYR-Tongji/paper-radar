from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer


def utcnow() -> datetime:
    return datetime.now(UTC)


class IdMixin:
    id = Column(Integer, primary_key=True, index=True)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

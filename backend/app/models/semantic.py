from sqlalchemy import JSON, Boolean, Column, Float, String, UniqueConstraint

from app.db.session import Base
from app.models.mixins import IdMixin, TimestampMixin

DEFAULT_MIN_SIMILARITY = 0.82
DEFAULT_SEMANTIC_WEIGHT = 0.75


class SemanticSettings(IdMixin, TimestampMixin, Base):
    __tablename__ = "semantic_settings"

    is_enabled = Column(Boolean, default=True, nullable=False)
    min_similarity = Column(Float, default=DEFAULT_MIN_SIMILARITY, nullable=False)
    semantic_weight = Column(Float, default=DEFAULT_SEMANTIC_WEIGHT, nullable=False)


class SemanticEmbedding(IdMixin, TimestampMixin, Base):
    __tablename__ = "semantic_embeddings"
    __table_args__ = (
        UniqueConstraint("model_key", "kind", "content_hash", name="uq_semantic_embedding_content"),
    )

    model_key = Column(String(256), index=True, nullable=False)
    kind = Column(String(16), nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    vector = Column(JSON, nullable=False)

"""Store local semantic settings, embeddings and explainable score evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0004"
down_revision: str | None = "20261007_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("semantic_settings"):
        op.create_table(
            "semantic_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("min_similarity", sa.Float(), nullable=False, server_default="0.82"),
            sa.Column("semantic_weight", sa.Float(), nullable=False, server_default="0.75"),
            *_timestamps(),
        )
    if not inspector.has_table("semantic_embeddings"):
        op.create_table(
            "semantic_embeddings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_key", sa.String(256), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("vector", sa.JSON(), nullable=False),
            *_timestamps(),
            sa.UniqueConstraint(
                "model_key", "kind", "content_hash", name="uq_semantic_embedding_content"
            ),
        )
        op.create_index("ix_semantic_embeddings_model_key", "semantic_embeddings", ["model_key"])
        op.create_index(
            "ix_semantic_embeddings_content_hash", "semantic_embeddings", ["content_hash"]
        )
    if inspector.has_table("paper_features"):
        columns = {column["name"] for column in inspector.get_columns("paper_features")}
        if "semantic_details" not in columns:
            op.add_column(
                "paper_features",
                sa.Column(
                    "semantic_details",
                    sa.JSON(),
                    nullable=False,
                    server_default="{}",
                ),
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("paper_features"):
        columns = {column["name"] for column in inspector.get_columns("paper_features")}
        if "semantic_details" in columns:
            op.drop_column("paper_features", "semantic_details")
    for table in ("semantic_embeddings", "semantic_settings"):
        if inspector.has_table(table):
            op.drop_table(table)

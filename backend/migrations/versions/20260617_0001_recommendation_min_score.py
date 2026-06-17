"""Add recommendation minimum score preference."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260617_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("user_preferences"):
        return
    columns = {column["name"] for column in inspector.get_columns("user_preferences")}
    if "recommendation_min_score" in columns:
        return
    op.add_column(
        "user_preferences",
        sa.Column(
            "recommendation_min_score",
            sa.Float(),
            nullable=False,
            server_default="50.0",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("user_preferences"):
        return
    columns = {column["name"] for column in inspector.get_columns("user_preferences")}
    if "recommendation_min_score" not in columns:
        return
    op.drop_column("user_preferences", "recommendation_min_score")

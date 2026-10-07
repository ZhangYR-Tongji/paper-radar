"""Track which scoring algorithm produced the cached paper scores."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261007_0003"
down_revision: str | None = "20260929_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("scoring_weights"):
        return
    columns = {column["name"] for column in inspector.get_columns("scoring_weights")}
    if "algorithm_version" not in columns:
        op.add_column(
            "scoring_weights",
            sa.Column(
                "algorithm_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )
    # Application startup performs the data migration and rescores in one
    # transaction, then records the current version only after success.


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("scoring_weights"):
        columns = {column["name"] for column in inspector.get_columns("scoring_weights")}
        if "algorithm_version" in columns:
            op.drop_column("scoring_weights", "algorithm_version")

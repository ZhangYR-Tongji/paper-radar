"""Track paged fetch progress and the run that first stored each paper."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0002"
down_revision: str | None = "20260617_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for table, columns in {
        "fetch_cursors": [
            sa.Column("pending_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pending_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_page_cursor", sa.Text(), nullable=True),
        ],
        "fetch_run_items": [sa.Column("resume_cursor", sa.Text(), nullable=True)],
        "papers": [
            sa.Column(
                "first_seen_run_id",
                sa.Integer(),
                sa.ForeignKey("fetch_runs.id"),
                nullable=True,
            ),
        ],
    }.items():
        inspector = sa.inspect(bind)
        if not inspector.has_table(table):
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)

    inspector = sa.inspect(bind)
    if inspector.has_table("papers"):
        indexes = {index["name"] for index in inspector.get_indexes("papers")}
        if "ix_papers_first_seen_run_id" not in indexes:
            op.create_index("ix_papers_first_seen_run_id", "papers", ["first_seen_run_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("papers"):
        op.drop_index("ix_papers_first_seen_run_id", table_name="papers")
    for table, names in {
        "papers": ["first_seen_run_id"],
        "fetch_run_items": ["resume_cursor"],
        "fetch_cursors": ["next_page_cursor", "pending_to", "pending_from"],
    }.items():
        if not sa.inspect(bind).has_table(table):
            continue
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for name in names:
            if name in existing:
                op.drop_column(table, name)

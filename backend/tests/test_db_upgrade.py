from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db import base as db_base
from app.db.session import Base
from app.models import FetchRun, Paper


def test_existing_database_gets_new_columns_and_run_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    started = datetime(2026, 9, 29, 10, tzinfo=UTC)
    with sessionmaker(bind=engine)() as db:
        run = FetchRun(
            status="success", started_at=started, finished_at=started + timedelta(minutes=1)
        )
        db.add(run)
        db.flush()
        run_id = run.id
        db.add(
            Paper(
                title="Legacy paper",
                normalized_title="legacy paper",
                source="arxiv",
                created_at=started + timedelta(seconds=30),
            ),
        )
        db.commit()

    with engine.begin() as connection:
        for table, removed in [
            ("fetch_cursors", {"pending_from", "pending_to", "next_page_cursor"}),
            ("fetch_run_items", {"resume_cursor"}),
            ("papers", {"first_seen_run_id"}),
        ]:
            columns = [
                column["name"]
                for column in inspect(connection).get_columns(table)
                if column["name"] not in removed
            ]
            names = ", ".join(columns)
            connection.execute(text(f"CREATE TABLE old_copy AS SELECT {names} FROM {table}"))
            connection.execute(text(f"DROP TABLE {table}"))
            connection.execute(text(f"ALTER TABLE old_copy RENAME TO {table}"))

    monkeypatch.setattr(db_base, "engine", engine)
    with sessionmaker(bind=engine)() as db:
        db_base.init_db(db)
        paper = db.query(Paper).one()
        assert paper.title == "Legacy paper"
        assert paper.first_seen_run_id == run_id
        assert db.query(FetchRun).one().status == "success"

    cursor_columns = {col["name"] for col in inspect(engine).get_columns("fetch_cursors")}
    item_columns = {col["name"] for col in inspect(engine).get_columns("fetch_run_items")}
    assert "next_page_cursor" in cursor_columns
    assert "resume_cursor" in item_columns
    engine.dispose()

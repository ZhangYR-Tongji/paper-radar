from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.fetch import clear_fetch_runs
from app.db.session import Base
from app.models import FetchCursor, FetchRun, FetchRunItem, KeywordGroup, Paper, SourceConfig
from app.schemas.fetch import ManualFetchRequest
from app.services.fetch_service import run_manual_fetch


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_manual_fetch_requires_keyword_group(db_session: Session) -> None:
    db_session.add(
        SourceConfig(
            source_name="openalex",
            display_name="OpenAlex",
            description="Open scholarly metadata index.",
            is_enabled=True,
            daily_limit=5,
        ),
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        run_manual_fetch(db_session, ManualFetchRequest())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "请先在设置中创建并启用至少一个关键词组。"


def test_clear_fetch_runs_deletes_fetch_records_only(db_session: Session) -> None:
    group = KeywordGroup(name="Aerial manipulation", positive_keywords=["aerial manipulation"])
    paper = Paper(
        title="AERMANI-PLACE",
        normalized_title="aermani place",
        authors=[],
        source="arxiv",
    )
    source = SourceConfig(
        source_name="arxiv",
        display_name="arXiv",
        description="Metadata search.",
        is_enabled=True,
        last_success_at=datetime.now(UTC),
        last_error_at=datetime.now(UTC),
        last_error_message="previous failure",
    )
    db_session.add_all([group, paper, source])
    db_session.flush()

    run = FetchRun(
        trigger_type="manual",
        status="success",
        started_at=datetime.now(UTC),
        enabled_sources=["arxiv"],
        enabled_keyword_groups=[{"id": group.id, "name": group.name}],
    )
    db_session.add(run)
    db_session.flush()
    db_session.add_all(
        [
            FetchRunItem(
                fetch_run_id=run.id,
                source_name="arxiv",
                keyword_group_id=group.id,
                status="success",
            ),
            FetchCursor(
                source_name="arxiv",
                keyword_group_id=group.id,
                last_run_id=run.id,
                last_status="success",
            ),
        ],
    )
    db_session.commit()

    result = clear_fetch_runs(db_session)

    assert result == {
        "deleted_runs": 1,
        "deleted_run_items": 1,
        "deleted_cursors": 1,
        "reset_sources": 1,
    }
    assert db_session.query(FetchRun).count() == 0
    assert db_session.query(FetchRunItem).count() == 0
    assert db_session.query(FetchCursor).count() == 0
    assert db_session.query(KeywordGroup).count() == 1
    assert db_session.query(Paper).count() == 1
    db_session.refresh(source)
    assert source.last_success_at is None
    assert source.last_error_at is None
    assert source.last_error_message is None


def test_clear_fetch_runs_rejects_running_fetch(db_session: Session) -> None:
    db_session.add(FetchRun(trigger_type="manual", status="running"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        clear_fetch_runs(db_session)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Fetch run 1 is still running."
    assert db_session.query(FetchRun).count() == 1

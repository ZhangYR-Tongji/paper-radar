from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models import SourceConfig
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

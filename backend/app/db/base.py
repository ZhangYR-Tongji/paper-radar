from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import Base, engine
from app.models import (
    FetchCursor,
    FetchRun,
    FetchRunItem,
    KeywordGroup,
    Paper,
    PaperFeature,
    ScoringWeights,
    SourceConfig,
    UserFeedback,
    UserPreferences,
)
from app.seed import seed_defaults

_MODEL_IMPORTS = (
    FetchCursor,
    FetchRun,
    FetchRunItem,
    KeywordGroup,
    Paper,
    PaperFeature,
    ScoringWeights,
    SourceConfig,
    UserFeedback,
    UserPreferences,
)


def init_db(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_user_preferences_schema()
    seed_defaults(db)
    recover_interrupted_fetch_runs(db)
    for index in FetchRun.__table__.indexes:
        index.create(bind=engine, checkfirst=True)


def recover_interrupted_fetch_runs(db: Session) -> None:
    interrupted = db.query(FetchRun).filter(FetchRun.status == "running").all()
    for run in interrupted:
        run.status = "failed"
        run.finished_at = run.finished_at or run.started_at
        run.error_count += 1
        run.error_summary = "检索进程中断，未完成的运行项可以重新检索。"
        for item in db.query(FetchRunItem).filter(
            FetchRunItem.fetch_run_id == run.id,
            FetchRunItem.status == "running",
        ):
            item.status = "failed"
            item.finished_at = item.finished_at or run.finished_at
            item.error_message = "检索进程中断。"
    if interrupted:
        db.commit()


def _ensure_user_preferences_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("user_preferences"):
        return
    columns = {column["name"] for column in inspector.get_columns("user_preferences")}
    if "recommendation_min_score" in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE user_preferences "
                "ADD COLUMN recommendation_min_score FLOAT NOT NULL DEFAULT 50.0",
            ),
        )

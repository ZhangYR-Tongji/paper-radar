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
from app.services.scoring import upgrade_scoring

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
    _ensure_fetch_schema()
    _ensure_scoring_schema()
    seed_defaults(db)
    recover_interrupted_fetch_runs(db)
    _backfill_first_seen_run(db)
    upgrade_scoring(db)
    for index in (*FetchRun.__table__.indexes, *Paper.__table__.indexes):
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


def _ensure_scoring_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("scoring_weights"):
        return
    columns = {column["name"] for column in inspector.get_columns("scoring_weights")}
    if "algorithm_version" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE scoring_weights "
                    "ADD COLUMN algorithm_version INTEGER NOT NULL DEFAULT 1"
                )
            )


def _ensure_fetch_schema() -> None:
    tables = {
        "fetch_cursors": {
            "pending_from": "DATETIME",
            "pending_to": "DATETIME",
            "next_page_cursor": "TEXT",
        },
        "fetch_run_items": {"resume_cursor": "TEXT"},
        "papers": {"first_seen_run_id": "INTEGER REFERENCES fetch_runs(id)"},
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, additions in tables.items():
            if not inspector.has_table(table):
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def _backfill_first_seen_run(db: Session) -> None:
    runs = (
        db.query(FetchRun)
        .filter(FetchRun.finished_at.is_not(None))
        .order_by(
            FetchRun.started_at,
        )
    )
    for run in runs:
        db.query(Paper).filter(
            Paper.first_seen_run_id.is_(None),
            Paper.created_at >= run.started_at,
            Paper.created_at <= run.finished_at,
        ).update({Paper.first_seen_run_id: run.id}, synchronize_session=False)
    db.commit()

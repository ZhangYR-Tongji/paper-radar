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

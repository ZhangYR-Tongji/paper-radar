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
    seed_defaults(db)

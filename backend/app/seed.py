from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.scoring import ScoringWeights
from app.models.source_config import SourceConfig

DEFAULT_SOURCES = [
    {
        "source_name": "arxiv",
        "display_name": "arXiv",
        "description": "Metadata search for arXiv preprints.",
        "is_enabled": True,
        "daily_limit": 100,
    },
    {
        "source_name": "openalex",
        "display_name": "OpenAlex",
        "description": "Open scholarly metadata index.",
        "is_enabled": True,
        "daily_limit": 100,
    },
    {
        "source_name": "crossref",
        "display_name": "Crossref",
        "description": "DOI and publisher metadata index.",
        "is_enabled": True,
        "daily_limit": 100,
    },
    {
        "source_name": "semantic_scholar",
        "display_name": "Semantic Scholar",
        "description": "Semantic Scholar academic metadata API.",
        "is_enabled": True,
        "daily_limit": 100,
    },
    {
        "source_name": "osf",
        "display_name": "OSF Preprints",
        "description": "OSF-hosted preprint metadata.",
        "is_enabled": False,
        "daily_limit": 50,
    },
]


def seed_defaults(db: Session) -> None:
    for source_data in DEFAULT_SOURCES:
        exists = (
            db.query(SourceConfig)
            .filter(SourceConfig.source_name == source_data["source_name"])
            .first()
        )
        if not exists:
            db.add(SourceConfig(**source_data))

    if not db.query(ScoringWeights).first():
        db.add(ScoringWeights())

    if not db.query(UserPreferences).first():
        db.add(UserPreferences())

    db.commit()

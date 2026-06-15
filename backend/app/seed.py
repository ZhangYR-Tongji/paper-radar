from sqlalchemy.orm import Session

from app.models.feedback import UserPreferences
from app.models.keyword_group import KeywordGroup
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

DEFAULT_KEYWORD_GROUPS = [
    {
        "name": "AI-assisted conceptual design",
        "description": "AI support for early-stage design ideation and concept development.",
        "priority_weight": 1.2,
        "positive_keywords": ["AI-assisted design", "conceptual design", "design ideation"],
        "required_keywords": ["design"],
        "optional_keywords": ["artificial intelligence", "human-AI", "ideation"],
        "related_tags": ["conceptual design", "human-ai collaboration"],
    },
    {
        "name": "Design cognition and reasoning",
        "description": "Design thinking, cognition, reasoning, and decision-making research.",
        "priority_weight": 1.0,
        "positive_keywords": ["design cognition", "design reasoning", "design thinking"],
        "required_keywords": ["design"],
        "optional_keywords": ["cognition", "reasoning", "decision making"],
        "related_tags": ["design cognition"],
    },
    {
        "name": "FBS / IBIS / Design Rationale",
        "description": "Function-behavior-structure, IBIS, and design rationale methods.",
        "priority_weight": 1.1,
        "positive_keywords": ["FBS", "IBIS", "design rationale"],
        "required_keywords": [],
        "optional_keywords": ["function behavior structure", "argumentation"],
        "related_tags": ["FBS", "IBIS", "design rationale"],
    },
    {
        "name": "Node-based and graph-based design tools",
        "description": "Graph, node, and network interfaces for design tooling.",
        "priority_weight": 1.0,
        "positive_keywords": ["node-based", "graph-based", "design tool"],
        "required_keywords": ["design"],
        "optional_keywords": ["knowledge graph", "visual programming", "workflow"],
        "related_tags": ["graph interface", "design tools"],
    },
    {
        "name": "Creativity support and Human-AI collaboration",
        "description": "Systems for creativity support and collaborative human-AI workflows.",
        "priority_weight": 1.0,
        "positive_keywords": ["creativity support", "human-AI collaboration", "co-creative"],
        "required_keywords": [],
        "optional_keywords": ["creative process", "mixed initiative", "collaboration"],
        "related_tags": ["creativity support", "human-ai collaboration"],
    },
    {
        "name": "User study and evaluation methods",
        "description": "Empirical evaluation and user study methods for design tools.",
        "priority_weight": 0.9,
        "positive_keywords": ["user study", "evaluation", "empirical study"],
        "required_keywords": [],
        "optional_keywords": ["controlled study", "interview", "metrics"],
        "related_tags": ["evaluation", "user study"],
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

    for group_data in DEFAULT_KEYWORD_GROUPS:
        exists = db.query(KeywordGroup).filter(KeywordGroup.name == group_data["name"]).first()
        if not exists:
            db.add(KeywordGroup(**group_data))

    if not db.query(ScoringWeights).first():
        db.add(ScoringWeights())

    if not db.query(UserPreferences).first():
        db.add(UserPreferences())

    db.commit()

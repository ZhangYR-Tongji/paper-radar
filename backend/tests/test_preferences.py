from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models import KeywordGroup, Paper, PaperFeature, ScoringWeights, UserPreferences
from app.schemas.feedback import FeedbackUpsert
from app.services.preferences import update_user_preferences_after_feedback
from app.services.scoring import score_paper


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


@pytest.mark.parametrize(
    ("rating", "keyword_weight", "context_weight", "negative_weight"),
    [
        (2, -0.1, -0.05, 0.1),
        (3, 0.05, 0.025, None),
        (4, 0.13, 0.065, None),
    ],
)
def test_intermediate_ratings_update_preferences(
    db_session: Session,
    rating: int,
    keyword_weight: float,
    context_weight: float,
    negative_weight: float | None,
) -> None:
    paper = _add_featured_paper(db_session)

    changed = update_user_preferences_after_feedback(
        db_session,
        paper.id,
        FeedbackUpsert(rating=rating, negative_feedback_tags=["off-topic"]),
    )

    preferences = db_session.query(UserPreferences).one()
    assert changed is True
    assert preferences.keyword_weights["human-AI"] == pytest.approx(keyword_weight)
    assert preferences.topic_weights["AI-assisted conceptual design"] == pytest.approx(
        context_weight,
    )
    assert preferences.method_weights["evaluation"] == pytest.approx(context_weight)
    assert preferences.venue_weights["CHI"] == pytest.approx(context_weight)
    if negative_weight is None:
        assert preferences.negative_keyword_weights == {}
    else:
        assert preferences.negative_keyword_weights["blockchain"] == pytest.approx(
            negative_weight,
        )
        assert preferences.negative_keyword_weights["off-topic"] == pytest.approx(
            negative_weight,
        )


def test_same_rating_does_not_accumulate_preferences(db_session: Session) -> None:
    paper = _add_featured_paper(db_session)

    update_user_preferences_after_feedback(
        db_session,
        paper.id,
        FeedbackUpsert(rating=4),
    )
    repeated = update_user_preferences_after_feedback(
        db_session,
        paper.id,
        FeedbackUpsert(rating=4),
        previous_rating=4,
    )
    upgraded = update_user_preferences_after_feedback(
        db_session,
        paper.id,
        FeedbackUpsert(rating=5),
        previous_rating=4,
    )

    preferences = db_session.query(UserPreferences).one()
    assert repeated is False
    assert upgraded is True
    assert preferences.keyword_weights["human-AI"] == pytest.approx(0.2)
    assert preferences.topic_weights["AI-assisted conceptual design"] == pytest.approx(0.1)
    assert preferences.method_weights["evaluation"] == pytest.approx(0.1)
    assert preferences.venue_weights["CHI"] == pytest.approx(0.1)


def test_user_preferences_affect_scoring(db_session: Session) -> None:
    db_session.add(
        KeywordGroup(
            name="Preferred topic",
            positive_keywords=["human-AI"],
            negative_keywords=["blockchain"],
        ),
    )
    db_session.add(
        ScoringWeights(
            topic_weight=0,
            method_weight=0,
            venue_weight=0,
            freshness_weight=0,
            user_preference_weight=1,
            negative_filter_weight=0,
        ),
    )
    db_session.add(
        UserPreferences(
            keyword_weights={"human-AI": 1.0},
            topic_weights={"Preferred topic": 1.0},
            method_weights={"evaluation": 1.0},
            venue_weights={"CHI": 1.0},
            negative_keyword_weights={"blockchain": 1.0},
        ),
    )
    preferred_paper = Paper(
        title="Human-AI evaluation for conceptual design",
        normalized_title="human ai evaluation for conceptual design",
        abstract="An evaluation study.",
        authors=[],
        source="test",
        venue="CHI",
    )
    penalized_paper = Paper(
        title="Human-AI evaluation with blockchain",
        normalized_title="human ai evaluation with blockchain",
        abstract="An evaluation study using blockchain.",
        authors=[],
        source="test",
        venue="CHI",
    )
    db_session.add_all([preferred_paper, penalized_paper])
    db_session.flush()

    preferred_feature = score_paper(db_session, preferred_paper)
    penalized_feature = score_paper(db_session, penalized_paper)

    assert preferred_feature.user_preference_score == pytest.approx(68.0)
    assert penalized_feature.user_preference_score == pytest.approx(63.0)
    assert preferred_feature.final_score > penalized_feature.final_score


def _add_featured_paper(db: Session) -> Paper:
    paper = Paper(
        title="Human-AI conceptual design evaluation",
        normalized_title="human ai conceptual design evaluation",
        abstract="A human-AI evaluation study for conceptual design.",
        authors=["Ada Lovelace"],
        source="test",
        source_id="paper-1",
        venue="CHI",
    )
    db.add(paper)
    db.flush()
    db.add(
        PaperFeature(
            paper_id=paper.id,
            matched_keyword_groups=["AI-assisted conceptual design"],
            matched_positive_keywords=["human-AI"],
            matched_negative_keywords=["blockchain"],
            method_tags=["evaluation"],
            final_score=50.0,
            classification="Worth Checking",
        ),
    )
    db.flush()
    return paper

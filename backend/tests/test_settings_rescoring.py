from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.papers import _upsert_feedback
from app.api.routes.settings import (
    clear_keyword_groups,
    create_keyword_group,
    delete_keyword_group,
    update_keyword_group,
    update_scoring_weights,
    update_source,
)
from app.db.session import Base
from app.models import (
    KeywordGroup,
    Paper,
    PaperFeature,
    ScoringWeights,
    SourceConfig,
    UserPreferences,
)
from app.schemas.feedback import FeedbackUpsert
from app.schemas.settings import (
    KeywordGroupCreate,
    KeywordGroupUpdate,
    ScoringWeightsUpdate,
    SourceConfigUpdate,
)
from app.services.scoring import score_paper


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as db:
        yield db
    engine.dispose()


def test_settings_changes_immediately_update_existing_papers(db_session: Session) -> None:
    source = SourceConfig(source_name="arxiv", display_name="arXiv")
    group = KeywordGroup(name="Robotics", positive_keywords=["robotics"])
    weights = ScoringWeights(
        topic_weight=1,
        method_weight=0,
        venue_weight=0,
        freshness_weight=0,
        user_preference_weight=0,
        negative_filter_weight=0,
    )
    paper = Paper(title="Robotics in flight", normalized_title="robotics in flight", source="arxiv")
    db_session.add_all([source, group, weights, paper, UserPreferences()])
    db_session.flush()
    score_paper(db_session, paper)
    db_session.commit()
    assert db_session.query(PaperFeature).one().final_score == 100

    update_source(source.id, SourceConfigUpdate(participates_in_ranking=False), db_session)
    assert db_session.query(PaperFeature).one().final_score == 0
    update_source(source.id, SourceConfigUpdate(participates_in_ranking=True), db_session)
    assert db_session.query(PaperFeature).one().final_score == 100

    update_keyword_group(group.id, KeywordGroupUpdate(positive_keywords=["geology"]), db_session)
    assert db_session.query(PaperFeature).one().final_score == 0
    update_keyword_group(group.id, KeywordGroupUpdate(positive_keywords=["robotics"]), db_session)
    assert db_session.query(PaperFeature).one().final_score == 100

    update_scoring_weights(ScoringWeightsUpdate(topic_weight=0), db_session)
    assert db_session.query(PaperFeature).one().final_score == 0

    update_scoring_weights(ScoringWeightsUpdate(topic_weight=1), db_session)
    delete_keyword_group(group.id, db_session)
    assert db_session.query(PaperFeature).one().final_score == 0
    create_keyword_group(
        KeywordGroupCreate(name="Robotics", positive_keywords=["robotics"]), db_session
    )
    assert db_session.query(PaperFeature).one().final_score == 100
    clear_keyword_groups(db_session)
    assert db_session.query(PaperFeature).one().final_score == 0


def test_rating_reuses_scoring_config_instead_of_querying_per_paper(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            KeywordGroup(name="Robotics", positive_keywords=["robotics"]),
            ScoringWeights(),
            UserPreferences(),
        ],
    )
    db_session.flush()
    for index in range(200):
        paper = Paper(
            title=f"Robotics case {index}",
            normalized_title=f"robotics case {index}",
            source="arxiv",
        )
        db_session.add(paper)
        db_session.flush()
        db_session.add(
            PaperFeature(
                paper_id=paper.id,
                matched_keyword_groups=["Robotics"],
                matched_positive_keywords=["robotics"],
                final_score=50,
                classification="Low Priority",
            ),
        )
    db_session.commit()

    selects = 0

    def count_selects(conn, cursor, statement, params, context, many) -> None:
        nonlocal selects
        if statement.lstrip().upper().startswith("SELECT"):
            selects += 1

    event.listen(db_session.bind, "before_cursor_execute", count_selects)
    _upsert_feedback(db_session, 1, FeedbackUpsert(rating=5))
    assert selects < 25
    assert db_session.query(PaperFeature).count() == 200

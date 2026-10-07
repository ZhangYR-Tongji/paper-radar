from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.db import base as db_base
from app.db.session import Base
from app.models import KeywordGroup, Paper, PaperFeature, ScoringWeights, UserFeedback
from app.models.scoring import DEFAULT_SCORING_WEIGHTS, LEGACY_SCORING_WEIGHTS, SCORING_VERSION
from app.schemas.settings import ScoringWeightsUpdate
from app.services import scoring


@pytest.mark.parametrize("custom_weights", [False, True])
def test_startup_upgrades_legacy_scores_once_and_preserves_user_data(monkeypatch, custom_weights):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    configured = dict(LEGACY_SCORING_WEIGHTS)
    if custom_weights:
        configured["topic_weight"] = 0.7
    with sessionmaker(bind=engine)() as db:
        db.add_all(
            [
                ScoringWeights(**configured),
                KeywordGroup(name="Robotics", positive_keywords=["tendon-driven robot"]),
            ]
        )
        paper = Paper(
            title="Tendon-driven robot kinematics",
            normalized_title="robot kinematics",
            source="arxiv",
            published_date=date.today(),
        )
        db.add(paper)
        db.flush()
        paper_id = paper.id
        db.add_all(
            [
                PaperFeature(paper_id=paper_id, final_score=1, classification="Filtered"),
                UserFeedback(paper_id=paper_id, is_saved=True, personal_note="Keep this note"),
            ]
        )
        db.commit()

    # Reproduce a pre-upgrade database with no version column.
    with engine.begin() as connection:
        columns = [
            column["name"]
            for column in inspect(connection).get_columns("scoring_weights")
            if column["name"] != "algorithm_version"
        ]
        connection.execute(
            text(f"CREATE TABLE legacy_weights AS SELECT {', '.join(columns)} FROM scoring_weights")
        )
        connection.execute(text("DROP TABLE scoring_weights"))
        connection.execute(text("ALTER TABLE legacy_weights RENAME TO scoring_weights"))

    monkeypatch.setattr(db_base, "engine", engine)
    with sessionmaker(bind=engine)() as db:
        db_base.init_db(db)
        weights = db.query(ScoringWeights).one()
        expected = configured if custom_weights else DEFAULT_SCORING_WEIGHTS
        assert {name: getattr(weights, name) for name in expected} == expected
        assert weights.algorithm_version == SCORING_VERSION
        feature = db.query(PaperFeature).one()
        assert feature.final_score > 1
        if not custom_weights:
            assert feature.classification == "Highly Relevant"
        assert db.query(Paper).one().id == paper_id
        feedback = db.query(UserFeedback).one()
        assert feedback.is_saved is True
        assert feedback.personal_note == "Keep this note"

        def unexpected_rescore(_db):
            pytest.fail("Current scores should not be recomputed at every startup")

        monkeypatch.setattr(scoring, "rescore_all_papers", unexpected_rescore)
        db_base.init_db(db)
    engine.dispose()


def test_failed_upgrade_rolls_back_version_and_default_weights(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add_all(
            [
                ScoringWeights(**LEGACY_SCORING_WEIGHTS),
                Paper(title="Legacy paper", normalized_title="legacy paper", source="arxiv"),
            ]
        )
        db.commit()

        def fail_scoring(*args):
            raise RuntimeError("simulated scoring failure")

        monkeypatch.setattr(scoring, "calculate_paper_score", fail_scoring)
        with pytest.raises(RuntimeError, match="simulated scoring failure"):
            scoring.upgrade_scoring(db)
        db.rollback()
        weights = db.query(ScoringWeights).one()
        assert weights.algorithm_version == 1
        assert weights.topic_weight == LEGACY_SCORING_WEIGHTS["topic_weight"]
        assert db.query(PaperFeature).count() == 0
    engine.dispose()


@pytest.mark.parametrize("invalid", [None, float("inf"), float("nan"), -0.1])
def test_settings_reject_weights_that_cannot_produce_valid_scores(invalid):
    with pytest.raises(ValidationError):
        ScoringWeightsUpdate(topic_weight=invalid)

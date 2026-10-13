from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db import base as db_base
from app.db.session import Base
from app.models import KeywordGroup, Paper, PaperFeature, ScoringWeights, UserFeedback
from app.models.scoring import SCORING_VERSION
from app.services import semantic_index


def test_startup_upgrades_old_database_without_model_inference(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        paper = Paper(title="Robot", normalized_title="robot", source="arxiv")
        db.add_all(
            [
                paper,
                ScoringWeights(algorithm_version=2),
                KeywordGroup(name="Robots", positive_keywords=["robot"]),
            ]
        )
        db.flush()
        db.add_all(
            [
                PaperFeature(paper_id=paper.id, final_score=80, classification="Highly Relevant"),
                UserFeedback(paper_id=paper.id, is_saved=True, personal_note="Important paper"),
            ]
        )
        db.commit()

    with engine.begin() as connection:
        columns = [
            c["name"]
            for c in inspect(connection).get_columns("paper_features")
            if c["name"] != "semantic_details"
        ]
        connection.execute(
            text(f"CREATE TABLE old_features AS SELECT {', '.join(columns)} FROM paper_features")
        )
        connection.execute(text("DROP TABLE paper_features"))
        connection.execute(text("ALTER TABLE old_features RENAME TO paper_features"))
        connection.execute(text("DROP TABLE semantic_embeddings"))
        connection.execute(text("DROP TABLE semantic_settings"))

    def unexpected_runtime():
        pytest.fail("Schema and startup scoring must not load or download a model")

    monkeypatch.setattr(db_base, "engine", engine)
    monkeypatch.setattr(semantic_index, "get_runtime", unexpected_runtime)
    with Session(engine) as db:
        db_base.init_db(db)
        assert db.query(Paper).count() == 1
        assert db.query(UserFeedback).one().personal_note == "Important paper"
        assert db.query(UserFeedback).one().is_saved is True
        assert db.query(ScoringWeights).one().algorithm_version == SCORING_VERSION
        feature = db.query(PaperFeature).one()
        assert feature.final_score > 0
        assert feature.semantic_details["status"] == "unavailable"
        db_base.init_db(db)
    engine.dispose()


def test_alembic_semantic_upgrade_is_repeatable_and_preserves_legacy_scores():
    migration = import_module("migrations.versions.20261013_0004_local_semantics")
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE paper_features (id INTEGER PRIMARY KEY, final_score FLOAT NOT NULL)")
        )
        connection.execute(text("INSERT INTO paper_features VALUES (1, 82.5)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.upgrade()
            assert connection.execute(
                text("SELECT final_score, semantic_details FROM paper_features")
            ).one() == (82.5, "{}")
            assert inspect(connection).has_table("semantic_embeddings")
            assert inspect(connection).has_table("semantic_settings")
            migration.downgrade()
            assert (
                connection.execute(text("SELECT final_score FROM paper_features")).scalar_one()
                == 82.5
            )
            assert not inspect(connection).has_table("semantic_embeddings")
    engine.dispose()

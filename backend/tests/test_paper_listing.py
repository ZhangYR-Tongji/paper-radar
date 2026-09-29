from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import FetchRun, Paper, PaperFeature, UserFeedback


def test_paper_filters_and_run_lists_page_at_database_boundary() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        first_run = FetchRun(status="success", started_at=datetime.now(UTC) - timedelta(days=1))
        second_run = FetchRun(status="success", started_at=datetime.now(UTC))
        db.add_all([first_run, second_run])
        db.flush()
        entries = [
            ("Robotics underwater study", first_run.id, 90, None),
            ("Robotics aerial study", first_run.id, 80, "saved"),
            ("Robotics field trial", second_run.id, 70, "read"),
            ("Geology field study", second_run.id, 60, None),
        ]
        for title, run_id, score, feedback_kind in entries:
            paper = Paper(
                title=title,
                normalized_title=title.lower(),
                source="arxiv",
                first_seen_run_id=run_id,
            )
            db.add(paper)
            db.flush()
            db.add(
                PaperFeature(
                    paper_id=paper.id,
                    final_score=score,
                    classification="Highly Relevant" if score >= 80 else "Worth Checking",
                ),
            )
            if feedback_kind == "saved":
                db.add(UserFeedback(paper_id=paper.id, is_saved=True))
            elif feedback_kind == "read":
                db.add(UserFeedback(paper_id=paper.id, is_read=True))
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        try:
            client = TestClient(app)
            unread = client.get(
                "/api/papers",
                params={"q": "robotics", "is_read": "false", "limit": 1, "offset": 0},
            )
            next_unread = client.get(
                "/api/papers",
                params={"q": "robotics", "is_read": "false", "limit": 1, "offset": 1},
            )
            assert unread.status_code == next_unread.status_code == 200
            assert [unread.json()[0]["title"], next_unread.json()[0]["title"]] == [
                "Robotics underwater study",
                "Robotics aerial study",
            ]

            latest = client.get("/api/papers/latest", params={"limit": 1})
            assert latest.status_code == 200
            assert [paper["title"] for paper in latest.json()["papers"]] == [
                "Robotics field trial"
            ]

            library = client.get("/api/papers/library", params={"limit": 1, "offset": 1})
            assert library.status_code == 200
            assert [paper["title"] for paper in library.json()] == ["Robotics field trial"]

            run_page = client.get(f"/api/fetch/runs/{first_run.id}", params={"limit": 1})
            assert run_page.status_code == 200
            assert [paper["title"] for paper in run_page.json()["papers"]] == [
                "Robotics underwater study"
            ]
        finally:
            app.dependency_overrides.clear()
    engine.dispose()

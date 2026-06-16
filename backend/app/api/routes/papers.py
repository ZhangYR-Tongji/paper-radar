from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.feedback import UserFeedback
from app.models.paper import Paper, PaperFeature
from app.schemas.feedback import FeedbackUpsert
from app.services.paper_views import latest_recommendations, list_paper_dicts, paper_to_dict
from app.services.preferences import update_user_preferences_after_feedback
from app.services.scoring import score_paper

router = APIRouter()


@router.get("")
def list_papers(
    min_score: float | None = None,
    classification: str | None = None,
    source: str | None = None,
    keyword_group: str | None = None,
    is_saved: bool | None = None,
    is_read: bool | None = None,
    is_core: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "score",
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_paper_dicts(
        db,
        min_score=min_score,
        classification=classification,
        source=source,
        keyword_group=keyword_group,
        is_saved=is_saved,
        is_read=is_read,
        is_core=is_core,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
    )


@router.get("/latest")
def latest_papers(db: Session = Depends(get_db)) -> dict[str, object]:
    return latest_recommendations(db)


@router.get("/library")
def library_papers(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    saved = list_paper_dicts(db, is_saved=True, sort_by="score")
    core = list_paper_dicts(db, is_core=True, sort_by="score")
    read = list_paper_dicts(db, is_read=True, sort_by="date")
    seen: set[int] = set()
    merged = []
    for paper in [*core, *saved, *read]:
        paper_id = int(paper["id"])
        if paper_id not in seen:
            seen.add(paper_id)
            merged.append(paper)
    return merged


@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    feature = db.query(PaperFeature).filter(PaperFeature.paper_id == paper_id).first()
    feedback = db.query(UserFeedback).filter(UserFeedback.paper_id == paper_id).first()
    return paper_to_dict(paper, feature, feedback)


@router.post("/{paper_id}/feedback")
def create_paper_feedback(
    paper_id: int,
    payload: FeedbackUpsert,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _upsert_feedback(db, paper_id, payload)


@router.put("/{paper_id}/feedback")
def update_paper_feedback(
    paper_id: int,
    payload: FeedbackUpsert,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _upsert_feedback(db, paper_id, payload)


def _upsert_feedback(db: Session, paper_id: int, payload: FeedbackUpsert) -> dict[str, object]:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    feedback = db.query(UserFeedback).filter(UserFeedback.paper_id == paper_id).first()
    previous_rating = feedback.rating if feedback else None
    if not feedback:
        feedback = UserFeedback(paper_id=paper_id)
        db.add(feedback)
    for field, value in payload.model_dump().items():
        setattr(feedback, field, value)
    preferences_changed = update_user_preferences_after_feedback(
        db,
        paper_id,
        payload,
        previous_rating=previous_rating,
    )
    if preferences_changed:
        for candidate in db.query(Paper).all():
            score_paper(db, candidate)
    db.commit()
    db.refresh(feedback)
    feature = db.query(PaperFeature).filter(PaperFeature.paper_id == paper_id).first()
    return paper_to_dict(paper, feature, feedback)

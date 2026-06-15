from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.feedback import UserFeedback
from app.models.paper import Paper

router = APIRouter()


@router.get("/history")
def feedback_history(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = (
        db.query(UserFeedback, Paper)
        .join(Paper, Paper.id == UserFeedback.paper_id)
        .order_by(UserFeedback.updated_at.desc())
        .all()
    )
    return [
        {
            "id": feedback.id,
            "paper_id": paper.id,
            "paper_title": paper.title,
            "rating": feedback.rating,
            "positive_feedback_tags": feedback.positive_feedback_tags,
            "negative_feedback_tags": feedback.negative_feedback_tags,
            "is_saved": feedback.is_saved,
            "is_core": feedback.is_core,
            "is_read": feedback.is_read,
            "is_ignored": feedback.is_ignored,
            "personal_note": feedback.personal_note,
            "updated_at": feedback.updated_at.isoformat(),
        }
        for feedback, paper in rows
    ]

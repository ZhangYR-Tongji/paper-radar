from app.schemas.feedback import FeedbackUpsert


def update_user_preferences_after_feedback(paper_id: int, feedback: FeedbackUpsert) -> None:
    raise NotImplementedError("Preference updates will be implemented with feedback persistence.")

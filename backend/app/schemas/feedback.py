from pydantic import BaseModel, Field


class FeedbackUpsert(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    positive_feedback_tags: list[str] = Field(default_factory=list)
    negative_feedback_tags: list[str] = Field(default_factory=list)
    is_saved: bool = False
    is_core: bool = False
    is_read: bool = False
    is_ignored: bool = False
    personal_note: str = ""

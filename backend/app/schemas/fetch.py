from datetime import datetime

from pydantic import BaseModel, Field


class ManualFetchRequest(BaseModel):
    mode: str = "since_last_success"
    source_names: list[str] = []
    keyword_group_ids: list[int] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    overlap_buffer_days: int = Field(default=3, ge=0)


class FetchStatusRead(BaseModel):
    is_running: bool = False
    current_run_id: int | None = None
    message: str = "No fetch is running."

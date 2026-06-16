from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ManualFetchRequest(BaseModel):
    mode: Literal["since_last_success", "custom_range", "historical_backfill"] = (
        "since_last_success"
    )
    source_names: list[str] = Field(default_factory=list)
    keyword_group_ids: list[int] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    overlap_buffer_days: int = Field(default=3, ge=0)


class FetchStatusRead(BaseModel):
    is_running: bool = False
    current_run_id: int | None = None
    message: str = "No fetch is running."

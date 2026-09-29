from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ManualFetchRequest(BaseModel):
    mode: Literal["since_last_success", "custom_range", "historical_backfill"] = (
        "since_last_success"
    )
    source_names: list[str] = Field(default_factory=list)
    keyword_group_ids: list[int] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    overlap_buffer_days: int = Field(default=3, ge=0)

    @model_validator(mode="after")
    def validate_date_range(self) -> "ManualFetchRequest":
        if self.mode in {"custom_range", "historical_backfill"}:
            if self.date_from is None:
                raise ValueError("date_from is required for custom range modes.")
            start = (
                self.date_from.replace(tzinfo=UTC)
                if self.date_from.tzinfo is None
                else self.date_from.astimezone(UTC)
            )
            end_value = self.date_to or datetime.now(UTC)
            end = (
                end_value.replace(tzinfo=UTC)
                if end_value.tzinfo is None
                else end_value.astimezone(UTC)
            )
            if start > end:
                raise ValueError("date_from must be earlier than date_to.")
        return self


class FetchStatusRead(BaseModel):
    is_running: bool = False
    current_run_id: int | None = None
    message: str = "No fetch is running."

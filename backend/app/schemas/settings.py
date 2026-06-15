from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_name: str
    display_name: str
    description: str
    is_enabled: bool
    daily_limit: int
    participates_in_ranking: bool
    metadata_only: bool
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None


class SourceConfigUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None
    daily_limit: int | None = Field(default=None, ge=0)
    participates_in_ranking: bool | None = None
    metadata_only: bool | None = None


class KeywordGroupBase(BaseModel):
    name: str
    description: str = ""
    is_enabled: bool = True
    priority_weight: float = Field(default=1.0, ge=0)
    positive_keywords: list[str] = []
    negative_keywords: list[str] = []
    required_keywords: list[str] = []
    optional_keywords: list[str] = []
    related_tags: list[str] = []


class KeywordGroupCreate(KeywordGroupBase):
    pass


class KeywordGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None
    priority_weight: float | None = Field(default=None, ge=0)
    positive_keywords: list[str] | None = None
    negative_keywords: list[str] | None = None
    required_keywords: list[str] | None = None
    optional_keywords: list[str] | None = None
    related_tags: list[str] | None = None


class KeywordGroupRead(KeywordGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ScoringWeightsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_weight: float
    method_weight: float
    venue_weight: float
    freshness_weight: float
    user_preference_weight: float
    negative_filter_weight: float
    updated_at: datetime


class ScoringWeightsUpdate(BaseModel):
    topic_weight: float | None = Field(default=None, ge=0)
    method_weight: float | None = Field(default=None, ge=0)
    venue_weight: float | None = Field(default=None, ge=0)
    freshness_weight: float | None = Field(default=None, ge=0)
    user_preference_weight: float | None = Field(default=None, ge=0)
    negative_filter_weight: float | None = Field(default=None, ge=0)

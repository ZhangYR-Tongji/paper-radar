from datetime import date

from pydantic import BaseModel, ConfigDict


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    abstract: str
    authors: list[str]
    published_date: date | None
    source: str
    source_id: str | None
    doi: str | None
    arxiv_id: str | None
    url: str | None
    pdf_url: str | None
    venue: str | None
    journal: str | None
    conference: str | None
    year: int | None

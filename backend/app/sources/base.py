from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel


class PaperResult(BaseModel):
    title: str
    abstract: str = ""
    authors: list[str] = []
    published_date: date | None = None
    updated_date: date | None = None
    source: str
    source_id: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    venue: str | None = None
    journal: str | None = None
    conference: str | None = None
    year: int | None = None


class BaseSourceAdapter(ABC):
    source_name: str

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int,
        date_from=None,
        date_to=None,
    ) -> list[PaperResult]:
        raise NotImplementedError


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def extract_year(value: date | None) -> int | None:
    if not value:
        return None
    return value.year

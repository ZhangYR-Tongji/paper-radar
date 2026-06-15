from datetime import date, datetime

import httpx

from app.sources.base import BaseSourceAdapter, PaperResult, clean_text, extract_year


class SemanticScholarAdapter(BaseSourceAdapter):
    source_name = "semantic_scholar"
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        params: dict[str, str | int] = {
            "query": query,
            "limit": min(limit, 100),
            "fields": (
                "title,abstract,authors,year,publicationDate,url,venue,"
                "externalIds,openAccessPdf,journal"
            ),
        }
        if date_from or date_to:
            params["year"] = _year_filter(date_from, date_to)

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            items = response.json().get("data", [])

        results: list[PaperResult] = []
        for item in items:
            published = _parse_date(item.get("publicationDate"))
            if not _within_range(published, date_from, date_to):
                continue
            external_ids = item.get("externalIds") or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")
            oa_pdf = item.get("openAccessPdf") or {}
            journal = item.get("journal") or {}
            results.append(
                PaperResult(
                    title=clean_text(item.get("title")),
                    abstract=clean_text(item.get("abstract")),
                    authors=[
                        author.get("name")
                        for author in item.get("authors", [])
                        if author.get("name")
                    ],
                    published_date=published,
                    updated_date=None,
                    source=self.source_name,
                    source_id=item.get("paperId"),
                    doi=doi.lower() if doi else None,
                    arxiv_id=arxiv_id,
                    url=item.get("url"),
                    pdf_url=oa_pdf.get("url"),
                    venue=item.get("venue") or journal.get("name"),
                    journal=journal.get("name"),
                    year=item.get("year") or extract_year(published),
                )
            )
        return results[:limit]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _year_filter(date_from=None, date_to=None) -> str:
    start = _as_date(date_from).year if date_from else ""
    end = _as_date(date_to).year if date_to else ""
    return f"{start}-{end}"


def _within_range(value: date | None, date_from=None, date_to=None) -> bool:
    if not value:
        return True
    if date_from and value < _as_date(date_from):
        return False
    if date_to and value > _as_date(date_to):
        return False
    return True


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value

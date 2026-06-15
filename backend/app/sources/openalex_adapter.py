from datetime import date, datetime

import httpx

from app.sources.base import BaseSourceAdapter, PaperResult, clean_text, extract_year


class OpenAlexAdapter(BaseSourceAdapter):
    source_name = "openalex"
    base_url = "https://api.openalex.org/works"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        filters = []
        if date_from:
            filters.append(f"from_publication_date:{_date_string(date_from)}")
        if date_to:
            filters.append(f"to_publication_date:{_date_string(date_to)}")

        params: dict[str, str | int] = {
            "search": query,
            "per-page": min(limit, 200),
            "sort": "publication_date:desc",
        }
        if filters:
            params["filter"] = ",".join(filters)

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        results: list[PaperResult] = []
        for item in payload.get("results", []):
            published = _parse_date(item.get("publication_date"))
            doi = _normalize_doi(item.get("doi"))
            primary_location = item.get("primary_location") or {}
            source = primary_location.get("source") or {}
            venue = source.get("display_name") or item.get("host_venue", {}).get("display_name")
            pdf_url = None
            best_oa_location = item.get("best_oa_location") or {}
            if best_oa_location:
                pdf_url = best_oa_location.get("pdf_url")

            results.append(
                PaperResult(
                    title=clean_text(item.get("title")),
                    abstract=_abstract_from_inverted_index(item.get("abstract_inverted_index")),
                    authors=[
                        author.get("author", {}).get("display_name")
                        for author in item.get("authorships", [])
                        if author.get("author", {}).get("display_name")
                    ],
                    published_date=published,
                    updated_date=None,
                    source=self.source_name,
                    source_id=item.get("id"),
                    doi=doi,
                    url=item.get("id") or item.get("doi"),
                    pdf_url=pdf_url,
                    venue=venue,
                    journal=venue if item.get("type") == "article" else None,
                    year=item.get("publication_year") or extract_year(published),
                )
            )
        return results[:limit]


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in index.items():
        positions.extend((position, word) for position in indexes)
    return clean_text(" ".join(word for _, word in sorted(positions)))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _date_string(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("https://doi.org/").lower()

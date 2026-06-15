from datetime import date, datetime

import httpx

from app.sources.base import BaseSourceAdapter, PaperResult, clean_text, extract_year


class CrossrefAdapter(BaseSourceAdapter):
    source_name = "crossref"
    base_url = "https://api.crossref.org/works"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        filters = []
        if date_from:
            filters.append(f"from-pub-date:{_date_string(date_from)}")
        if date_to:
            filters.append(f"until-pub-date:{_date_string(date_to)}")
        params: dict[str, str | int] = {
            "query.bibliographic": query,
            "rows": min(limit, 100),
            "sort": "published",
            "order": "desc",
        }
        if filters:
            params["filter"] = ",".join(filters)

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            items = response.json().get("message", {}).get("items", [])

        results: list[PaperResult] = []
        for item in items:
            published = _date_from_parts(
                item.get("published-print")
                or item.get("published-online")
                or item.get("published")
                or item.get("issued")
            )
            title = clean_text((item.get("title") or [""])[0])
            if not title:
                continue
            doi = item.get("DOI")
            container = item.get("container-title") or []
            venue = container[0] if container else item.get("publisher")
            results.append(
                PaperResult(
                    title=title,
                    abstract=clean_text(item.get("abstract")),
                    authors=[
                        clean_text(
                            " ".join(
                                part
                                for part in [author.get("given"), author.get("family")]
                                if part
                            )
                        )
                        for author in item.get("author", [])
                    ],
                    published_date=published,
                    updated_date=None,
                    source=self.source_name,
                    source_id=doi or item.get("URL"),
                    doi=doi.lower() if doi else None,
                    url=item.get("URL"),
                    pdf_url=None,
                    venue=venue,
                    journal=venue,
                    year=extract_year(published),
                )
            )
        return results[:limit]


def _date_from_parts(value: dict | None) -> date | None:
    parts = (value or {}).get("date-parts") or []
    if not parts or not parts[0]:
        return None
    year = parts[0][0]
    month = parts[0][1] if len(parts[0]) > 1 else 1
    day = parts[0][2] if len(parts[0]) > 2 else 1
    return date(year, month, day)


def _date_string(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()

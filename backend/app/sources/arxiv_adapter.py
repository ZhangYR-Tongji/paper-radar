from datetime import date, datetime

import arxiv

from app.sources.base import BaseSourceAdapter, PaperResult, SearchPage, clean_text, extract_year


class ArxivAdapter(BaseSourceAdapter):
    source_name = "arxiv"

    def search_page(
        self, query: str, limit: int, date_from=None, date_to=None, cursor: str | None = None
    ) -> SearchPage:
        offset = int(cursor or 0)
        if offset >= 30_000:
            raise ValueError("arXiv result window exceeds its 30,000-result paging limit.")
        client = arxiv.Client(page_size=min(max(limit + 1, 1), 100), delay_seconds=3.0)
        date_filter = _submitted_date_filter(date_from, date_to)
        search = arxiv.Search(
            query=f"({query}) AND {date_filter}" if date_filter else query,
            max_results=offset + limit + 1,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        results: list[PaperResult] = []
        raw_items = list(client.results(search, offset=offset))
        for item in raw_items[:limit]:
            published = _to_date(item.published)
            updated = _to_date(item.updated)
            comparable_date = published or updated
            if not _within_range(comparable_date, date_from, date_to):
                continue

            doi = getattr(item, "doi", None)
            arxiv_id = item.get_short_id()
            results.append(
                PaperResult(
                    title=clean_text(item.title),
                    abstract=clean_text(item.summary),
                    authors=[author.name for author in item.authors],
                    published_date=published,
                    updated_date=updated,
                    source=self.source_name,
                    source_id=item.entry_id,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=item.entry_id,
                    pdf_url=item.pdf_url,
                    venue="arXiv preprint",
                    year=extract_year(published),
                )
            )
        next_cursor = str(offset + limit) if len(raw_items) > limit else None
        return SearchPage(results, next_cursor)


def _submitted_date_filter(date_from=None, date_to=None) -> str | None:
    if not date_from and not date_to:
        return None
    start = _as_date(date_from).strftime("%Y%m%d") + "0000" if date_from else "000101010000"
    end = _as_date(date_to).strftime("%Y%m%d") + "2359" if date_to else "999912312359"
    return f"submittedDate:[{start} TO {end}]"


def _to_date(value: datetime | None) -> date | None:
    if not value:
        return None
    return value.date()


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

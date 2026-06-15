from datetime import date, datetime

import arxiv

from app.sources.base import BaseSourceAdapter, PaperResult, clean_text, extract_year


class ArxivAdapter(BaseSourceAdapter):
    source_name = "arxiv"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        client = arxiv.Client(page_size=min(max(limit, 1), 100), delay_seconds=0.5)
        search = arxiv.Search(
            query=query,
            max_results=max(limit * 2, limit),
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        results: list[PaperResult] = []
        for item in client.results(search):
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
            if len(results) >= limit:
                break
        return results


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

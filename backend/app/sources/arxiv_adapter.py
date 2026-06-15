from app.sources.base import BaseSourceAdapter, PaperResult


class ArxivAdapter(BaseSourceAdapter):
    source_name = "arxiv"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        raise NotImplementedError("arXiv adapter will be implemented after settings APIs.")

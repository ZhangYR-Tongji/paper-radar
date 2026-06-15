from app.sources.base import BaseSourceAdapter, PaperResult


class OpenAlexAdapter(BaseSourceAdapter):
    source_name = "openalex"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        raise NotImplementedError("OpenAlex adapter will be implemented after arXiv.")

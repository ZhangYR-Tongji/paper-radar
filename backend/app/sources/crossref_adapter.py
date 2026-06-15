from app.sources.base import BaseSourceAdapter, PaperResult


class CrossrefAdapter(BaseSourceAdapter):
    source_name = "crossref"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        raise NotImplementedError("Crossref adapter is scaffolded for the MVP sequence.")

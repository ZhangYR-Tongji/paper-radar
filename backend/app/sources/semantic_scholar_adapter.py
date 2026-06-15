from app.sources.base import BaseSourceAdapter, PaperResult


class SemanticScholarAdapter(BaseSourceAdapter):
    source_name = "semantic_scholar"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        raise NotImplementedError("Semantic Scholar adapter is scaffolded for the MVP sequence.")

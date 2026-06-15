from app.sources.base import BaseSourceAdapter, PaperResult


class OsfAdapter(BaseSourceAdapter):
    source_name = "osf"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        raise NotImplementedError("OSF adapter is scaffolded and disabled by default.")

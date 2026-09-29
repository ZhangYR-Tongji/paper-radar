from app.sources.base import BaseSourceAdapter, SearchPage


class OsfAdapter(BaseSourceAdapter):
    source_name = "osf"

    def search_page(
        self, query: str, limit: int, date_from=None, date_to=None, cursor: str | None = None
    ) -> SearchPage:
        raise NotImplementedError("OSF Preprints is not implemented yet; disable this source.")

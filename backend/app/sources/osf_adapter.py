from app.sources.base import BaseSourceAdapter, PaperResult


class OsfAdapter(BaseSourceAdapter):
    source_name = "osf"

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        # OSF is seeded as disabled. Keep this adapter non-failing so users can enable it
        # later without breaking the manual fetch flow while a richer implementation lands.
        return []

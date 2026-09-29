from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from app.sources.arxiv_adapter import ArxivAdapter
from app.sources.crossref_adapter import CrossrefAdapter
from app.sources.openalex_adapter import OpenAlexAdapter
from app.sources.semantic_scholar_adapter import SemanticScholarAdapter


def test_arxiv_requests_historical_window_before_paging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []
    offsets: list[int] = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def results(self, search, offset=0):
            queries.append(search.query)
            offsets.append(offset)
            for index in range(offset, 3):
                yield SimpleNamespace(
                    published=datetime(2024, 2, 1, tzinfo=UTC),
                    updated=datetime(2024, 2, 1, tzinfo=UTC),
                    title=f"Research paper {index}",
                    summary="Research abstract",
                    authors=[],
                    entry_id=f"https://arxiv.org/abs/{index}",
                    doi=None,
                    get_short_id=lambda index=index: str(index),
                    pdf_url=None,
                )

    monkeypatch.setattr("app.sources.arxiv_adapter.arxiv.Client", FakeClient)
    adapter = ArxivAdapter()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 3, 1, tzinfo=UTC)
    first = adapter.search_page("research", 2, start, end)
    second = adapter.search_page("research", 2, start, end, first.next_cursor)

    assert "submittedDate:[202401010000 TO 202403012359]" in queries[0]
    assert offsets == [0, 2]
    assert [len(first.papers), len(second.papers)] == [2, 1]
    assert first.next_cursor == "2"
    assert second.next_cursor is None


def test_openalex_uses_cursor_paging(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def respond(params):
        seen.append(params["cursor"])
        if params["cursor"] == "*":
            return {"meta": {"next_cursor": "page-two"}, "results": [{"title": "First"}]}
        return {"meta": {"next_cursor": None}, "results": [{"title": "Second"}]}

    _mock_client(monkeypatch, respond)
    adapter = OpenAlexAdapter()
    first = adapter.search_page("research", 1)
    second = adapter.search_page("research", 1, cursor=first.next_cursor)

    assert seen == ["*", "page-two"]
    assert [paper.title for paper in first.papers + second.papers] == ["First", "Second"]
    assert second.next_cursor is None


def test_crossref_uses_cursor_paging(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def respond(params):
        seen.append(params["cursor"])
        if params["cursor"] == "*":
            return {"message": {"next-cursor": "page-two", "items": [{"title": ["First"]}]}}
        return {"message": {"next-cursor": "page-three", "items": []}}

    _mock_client(monkeypatch, respond)
    adapter = CrossrefAdapter()
    first = adapter.search_page("research", 1)
    second = adapter.search_page("research", 1, cursor=first.next_cursor)

    assert seen == ["*", "page-two"]
    assert first.next_cursor == "page-two"
    assert second.next_cursor is None


def test_semantic_scholar_reports_result_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_client(
        monkeypatch,
        lambda params: {"data": [{"title": "First"}], "total": 1001},
    )
    with pytest.raises(ValueError, match="capped"):
        SemanticScholarAdapter().search_page("research", 1)


def _mock_client(monkeypatch: pytest.MonkeyPatch, respond) -> None:
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url, params):
            return httpx.Response(200, json=respond(params), request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "Client", FakeClient)

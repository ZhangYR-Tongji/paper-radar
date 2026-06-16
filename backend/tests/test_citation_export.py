from datetime import date

from app.models import Paper
from app.services.citation_export import export_bibtex, export_filename, export_ris


def test_export_ris_contains_zotero_import_fields() -> None:
    paper = _paper()

    content = export_ris([paper])

    assert "TY  - JOUR" in content
    assert "TI  - Human-AI Evaluation for Scientific Writing" in content
    assert "AU  - Ada Lovelace" in content
    assert "PY  - 2026" in content
    assert "DA  - 2026-06-16" in content
    assert "T2  - Journal of Research Tools" in content
    assert "DO  - 10.1234/example" in content
    assert "UR  - https://example.org/paper" in content
    assert "L1  - https://example.org/paper.pdf" in content
    assert content.endswith("ER  -\r\n")


def test_export_bibtex_contains_zotero_import_fields() -> None:
    paper = _paper()

    content = export_bibtex([paper])

    assert "@article{Lovelace2026HumanAIEvaluationFor" in content
    assert "title = {Human-AI Evaluation for Scientific Writing}" in content
    assert "author = {Ada Lovelace and Alan Turing}" in content
    assert "year = {2026}" in content
    assert "journal = {Journal of Research Tools}" in content
    assert "doi = {10.1234/example}" in content
    assert "url = {https://example.org/paper}" in content
    assert "file = {https://example.org/paper.pdf}" in content


def test_export_filename_uses_zotero_friendly_extensions() -> None:
    assert export_filename("Paper Radar Library", "ris") == "paper-radar-library.ris"
    assert export_filename("Paper Radar Library", "bibtex") == "paper-radar-library.bib"


def _paper() -> Paper:
    return Paper(
        title="Human-AI Evaluation for Scientific Writing",
        normalized_title="human ai evaluation for scientific writing",
        abstract="A study about human-AI writing tools.",
        authors=["Ada Lovelace", "Alan Turing"],
        published_date=date(2026, 6, 16),
        source="openalex",
        source_id="W1",
        doi="10.1234/example",
        url="https://example.org/paper",
        pdf_url="https://example.org/paper.pdf",
        venue="Journal of Research Tools",
        journal="Journal of Research Tools",
        year=2026,
    )

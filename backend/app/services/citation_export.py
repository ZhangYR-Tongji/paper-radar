import re
from collections.abc import Sequence

from app.models.paper import Paper

EXPORT_MEDIA_TYPES = {
    "ris": "application/x-research-info-systems; charset=utf-8",
    "bibtex": "application/x-bibtex; charset=utf-8",
}


def export_papers(papers: Sequence[Paper], export_format: str) -> str:
    if export_format == "ris":
        return export_ris(papers)
    if export_format == "bibtex":
        return export_bibtex(papers)
    raise ValueError(f"Unsupported export format: {export_format}")


def export_ris(papers: Sequence[Paper]) -> str:
    entries = [_paper_to_ris(paper) for paper in papers]
    return "\r\n".join(entries) + ("\r\n" if entries else "")


def export_bibtex(papers: Sequence[Paper]) -> str:
    used_keys: set[str] = set()
    entries = [_paper_to_bibtex(paper, used_keys) for paper in papers]
    return "\n\n".join(entries) + ("\n" if entries else "")


def export_filename(base_name: str, export_format: str) -> str:
    extension = "ris" if export_format == "ris" else "bib"
    safe_base = re.sub(r"[^A-Za-z0-9_-]+", "-", base_name).strip("-").lower()
    return f"{safe_base or 'paper-radar-export'}.{extension}"


def export_media_type(export_format: str) -> str:
    return EXPORT_MEDIA_TYPES[export_format]


def _paper_to_ris(paper: Paper) -> str:
    lines = [f"TY  - {_ris_type(paper)}"]
    _append_ris(lines, "TI", paper.title)
    for author in paper.authors or []:
        _append_ris(lines, "AU", author)
    _append_ris(lines, "AB", paper.abstract)
    if paper.year:
        _append_ris(lines, "PY", str(paper.year))
    if paper.published_date:
        _append_ris(lines, "DA", paper.published_date.isoformat())
    _append_ris(lines, "T2", paper.journal or paper.conference or paper.venue)
    _append_ris(lines, "DO", paper.doi)
    _append_ris(lines, "UR", paper.url)
    _append_ris(lines, "L1", paper.pdf_url)
    if paper.arxiv_id:
        _append_ris(lines, "AN", f"arXiv:{paper.arxiv_id}")
    lines.append("ER  -")
    return "\r\n".join(lines)


def _paper_to_bibtex(paper: Paper, used_keys: set[str]) -> str:
    entry_type = _bibtex_type(paper)
    citation_key = _citation_key(paper, used_keys)
    fields = [
        ("title", paper.title),
        ("author", " and ".join(paper.authors or [])),
        ("year", str(paper.year) if paper.year else None),
        ("journal", paper.journal if entry_type == "article" else None),
        ("booktitle", paper.conference if entry_type == "inproceedings" else None),
        (
            "venue",
            paper.venue if paper.venue and not paper.journal and not paper.conference else None,
        ),
        ("doi", paper.doi),
        ("url", paper.url),
        ("abstract", paper.abstract),
        ("eprint", paper.arxiv_id),
        ("file", paper.pdf_url),
    ]
    rendered_fields = [
        f"  {name} = {{{_escape_bibtex(value)}}}"
        for name, value in fields
        if value
    ]
    return f"@{entry_type}{{{citation_key},\n" + ",\n".join(rendered_fields) + "\n}"


def _append_ris(lines: list[str], tag: str, value: str | None) -> None:
    if value:
        cleaned = _one_line(value)
        if cleaned:
            lines.append(f"{tag}  - {cleaned}")


def _ris_type(paper: Paper) -> str:
    if paper.conference:
        return "CONF"
    if paper.journal:
        return "JOUR"
    return "GEN"


def _bibtex_type(paper: Paper) -> str:
    if paper.journal:
        return "article"
    if paper.conference:
        return "inproceedings"
    return "misc"


def _citation_key(paper: Paper, used_keys: set[str]) -> str:
    first_author = (paper.authors or ["Paper"])[0]
    author_token = re.sub(r"[^A-Za-z0-9]+", "", first_author.split()[-1]) or "Paper"
    year_token = str(paper.year or "n.d.").replace(".", "")
    title_words = re.findall(r"[A-Za-z0-9]+", paper.title)[:4]
    title_token = "".join(word[:1].upper() + word[1:] for word in title_words)
    base_key = f"{author_token}{year_token}{title_token}"[:80] or "PaperRadarExport"
    key = base_key
    suffix = 2
    while key in used_keys:
        key = f"{base_key}{suffix}"
        suffix += 1
    used_keys.add(key)
    return key


def _escape_bibtex(value: str) -> str:
    return _one_line(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _one_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

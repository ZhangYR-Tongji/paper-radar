import re
import unicodedata

from rapidfuzz import fuzz
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.sources.base import PaperResult


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized.strip()


def find_duplicate_paper(db: Session, result: PaperResult) -> Paper | None:
    doi = _normalize_optional(result.doi)
    arxiv_id = _normalize_optional(result.arxiv_id)
    normalized_title = normalize_title(result.title)

    if doi:
        paper = db.query(Paper).filter(Paper.doi == doi).first()
        if paper:
            return paper

    if arxiv_id:
        paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        if paper:
            return paper

    paper = db.query(Paper).filter(Paper.normalized_title == normalized_title).first()
    if paper:
        return paper

    candidates = (
        db.query(Paper)
        .filter(
            or_(
                Paper.year == result.year,
                Paper.source == result.source,
                Paper.year.is_(None),
            )
        )
        .limit(200)
        .all()
    )

    result_authors = {_author_key(author) for author in result.authors}
    for candidate in candidates:
        similarity = fuzz.ratio(normalized_title, candidate.normalized_title) / 100
        if similarity > 0.92:
            return candidate
        candidate_authors = {_author_key(author) for author in candidate.authors}
        if similarity > 0.86 and result_authors.intersection(candidate_authors):
            return candidate

    return None


def _normalize_optional(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def _author_key(author: str) -> str:
    return normalize_title(author).replace(" ", "")

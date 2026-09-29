from datetime import date, datetime, timedelta

from sqlalchemy import String, case, cast, or_
from sqlalchemy.orm import Session

from app.models.feedback import UserFeedback, UserPreferences
from app.models.fetch import FetchRun, FetchRunItem
from app.models.paper import Paper, PaperFeature


def paper_to_dict(
    paper: Paper,
    feature: PaperFeature | None = None,
    feedback: UserFeedback | None = None,
) -> dict[str, object]:
    feature = feature or PaperFeature(
        paper_id=paper.id,
        final_score=0,
        classification="Filtered",
    )
    return {
        "id": paper.id,
        "score": feature.final_score,
        "classification": feature.classification,
        "title": paper.title,
        "normalized_title": paper.normalized_title,
        "abstract": paper.abstract,
        "authors": paper.authors or [],
        "published_date": _date_string(paper.published_date),
        "updated_date": _date_string(paper.updated_date),
        "source": paper.source,
        "source_id": paper.source_id,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "venue": paper.venue,
        "journal": paper.journal,
        "conference": paper.conference,
        "year": paper.year,
        "matched_keyword_groups": feature.matched_keyword_groups or [],
        "matched_positive_keywords": feature.matched_positive_keywords or [],
        "matched_negative_keywords": feature.matched_negative_keywords or [],
        "topic_tags": feature.topic_tags or [],
        "method_tags": feature.method_tags or [],
        "rating": feedback.rating if feedback else None,
        "positive_feedback_tags": feedback.positive_feedback_tags if feedback else [],
        "negative_feedback_tags": feedback.negative_feedback_tags if feedback else [],
        "is_saved": feedback.is_saved if feedback else False,
        "is_core": feedback.is_core if feedback else False,
        "is_read": feedback.is_read if feedback else False,
        "is_ignored": feedback.is_ignored if feedback else False,
        "personal_note": feedback.personal_note if feedback else "",
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }


def list_paper_dicts(
    db: Session,
    min_score: float | None = None,
    classification: str | None = None,
    source: str | None = None,
    keyword_group: str | None = None,
    is_saved: bool | None = None,
    is_read: bool | None = None,
    is_core: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = "score",
    run: FetchRun | None = None,
    is_ignored: bool | None = None,
    in_library: bool = False,
    search_query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    query = (
        db.query(Paper, PaperFeature, UserFeedback)
        .outerjoin(PaperFeature, PaperFeature.paper_id == Paper.id)
        .outerjoin(UserFeedback, UserFeedback.paper_id == Paper.id)
    )
    if source:
        query = query.filter(Paper.source == source)
    if date_from:
        query = query.filter(Paper.published_date >= date_from)
    if date_to:
        query = query.filter(Paper.published_date <= date_to)
    if min_score is not None:
        query = query.filter(PaperFeature.final_score >= min_score)
    if classification:
        query = query.filter(PaperFeature.classification == classification)
    if search_query:
        escaped = (
            search_query.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        query = query.filter(
            or_(
                Paper.title.ilike(pattern, escape="\\"),
                Paper.abstract.ilike(pattern, escape="\\"),
                cast(Paper.authors, String).ilike(pattern, escape="\\"),
                cast(PaperFeature.matched_keyword_groups, String).ilike(pattern, escape="\\"),
                cast(PaperFeature.matched_positive_keywords, String).ilike(
                    pattern, escape="\\"
                ),
            )
        )
    if is_saved is not None:
        query = query.filter(
            or_(UserFeedback.paper_id.is_(None), UserFeedback.is_saved.is_(False))
            if not is_saved
            else UserFeedback.is_saved.is_(True)
        )
    if is_read is not None:
        query = query.filter(
            or_(UserFeedback.paper_id.is_(None), UserFeedback.is_read.is_(False))
            if not is_read
            else UserFeedback.is_read.is_(True)
        )
    if is_core is not None:
        query = query.filter(
            or_(UserFeedback.paper_id.is_(None), UserFeedback.is_core.is_(False))
            if not is_core
            else UserFeedback.is_core.is_(True)
        )
    if is_ignored is not None:
        query = query.filter(
            or_(UserFeedback.paper_id.is_(None), UserFeedback.is_ignored.is_(False))
            if not is_ignored
            else UserFeedback.is_ignored.is_(True)
        )
    if in_library:
        query = query.filter(
            or_(
                UserFeedback.is_saved.is_(True),
                UserFeedback.is_core.is_(True),
                UserFeedback.is_read.is_(True),
            )
        )
    if run:
        query = query.filter(Paper.first_seen_run_id == run.id)

    if sort_by == "library":
        priority = case(
            (UserFeedback.is_core.is_(True), 0),
            (UserFeedback.is_saved.is_(True), 1),
            (UserFeedback.is_read.is_(True), 2),
            else_=3,
        )
        query = query.order_by(priority, PaperFeature.final_score.desc(), Paper.id.desc())
    elif sort_by == "date":
        query = query.order_by(Paper.published_date.desc(), Paper.id.desc())
    elif sort_by == "created_at":
        query = query.order_by(Paper.created_at.desc(), Paper.id.desc())
    else:
        query = query.order_by(PaperFeature.final_score.desc(), Paper.id.desc())

    if keyword_group:
        rows = [
            row
            for row in query.all()
            if row[1] and keyword_group in (row[1].matched_keyword_groups or [])
        ]
        rows = rows[offset : offset + limit if limit is not None else None]
    else:
        if limit is not None:
            query = query.limit(limit)
        rows = query.offset(offset).all()
    papers = [paper_to_dict(paper, feature, feedback) for paper, feature, feedback in rows]
    return papers


def latest_recommendations(
    db: Session, limit: int | None = None, offset: int = 0
) -> dict[str, object]:
    run = db.query(FetchRun).order_by(FetchRun.started_at.desc(), FetchRun.id.desc()).first()
    min_score = _recommendation_min_score(db)
    if not run:
        return {
            "latest_fetch_run": None,
            "recommendation_min_score": min_score,
            "papers": [],
        }

    papers = list_paper_dicts(
        db,
        min_score=min_score,
        sort_by="score",
        run=run,
        is_ignored=False,
        limit=limit,
        offset=offset,
    )
    return {
        "latest_fetch_run": fetch_run_to_dict(db, run, include_items=False, include_papers=False),
        "recommendation_min_score": min_score,
        "papers": papers,
    }


def fetch_run_to_dict(
    db: Session,
    run: FetchRun | None,
    *,
    include_items: bool = True,
    include_papers: bool = True,
    paper_limit: int | None = None,
    paper_offset: int = 0,
) -> dict[str, object] | None:
    if not run:
        return None
    items = (
        db.query(FetchRunItem)
        .filter(FetchRunItem.fetch_run_id == run.id)
        .order_by(FetchRunItem.id)
        .all()
        if include_items
        else []
    )
    return {
        "id": run.id,
        "trigger_type": run.trigger_type,
        "status": run.status,
        "started_at": _datetime_string(run.started_at),
        "finished_at": _datetime_string(run.finished_at),
        "requested_from": _datetime_string(run.requested_from),
        "requested_to": _datetime_string(run.requested_to),
        "overlap_buffer_days": run.overlap_buffer_days,
        "enabled_sources": run.enabled_sources,
        "enabled_keyword_groups": run.enabled_keyword_groups,
        "total_raw_results": run.total_raw_results,
        "total_new_papers": run.total_new_papers,
        "total_duplicate_papers": run.total_duplicate_papers,
        "total_scored_papers": run.total_scored_papers,
        "total_highly_relevant": run.total_highly_relevant,
        "total_low_priority": run.total_low_priority,
        "error_count": run.error_count,
        "error_summary": run.error_summary,
        "items": [fetch_run_item_to_dict(item) for item in items],
        "papers": (
            list_paper_dicts(
                db, run=run, sort_by="score", limit=paper_limit, offset=paper_offset
            )
            if include_papers
            else []
        ),
    }


def fetch_run_item_to_dict(item: FetchRunItem) -> dict[str, object]:
    return {
        "id": item.id,
        "fetch_run_id": item.fetch_run_id,
        "source_name": item.source_name,
        "keyword_group_id": item.keyword_group_id,
        "fetch_from": _datetime_string(item.fetch_from),
        "fetch_to": _datetime_string(item.fetch_to),
        "status": item.status,
        "raw_result_count": item.raw_result_count,
        "new_paper_count": item.new_paper_count,
        "duplicate_count": item.duplicate_count,
        "error_message": item.error_message,
        "started_at": _datetime_string(item.started_at),
        "finished_at": _datetime_string(item.finished_at),
    }


def default_latest_date_from(days: int = 30) -> date:
    return date.today() - timedelta(days=days)


def _recommendation_min_score(db: Session) -> float:
    preferences = db.query(UserPreferences).first()
    if not preferences or preferences.recommendation_min_score is None:
        return 50.0
    return float(preferences.recommendation_min_score)


def _date_string(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_string(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

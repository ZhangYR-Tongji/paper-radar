from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.feedback import UserFeedback
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
    if is_saved is not None:
        query = query.filter(UserFeedback.is_saved.is_(is_saved))
    if is_read is not None:
        query = query.filter(UserFeedback.is_read.is_(is_read))
    if is_core is not None:
        query = query.filter(UserFeedback.is_core.is_(is_core))
    if run and run.started_at:
        query = query.filter(Paper.created_at >= run.started_at)

    rows = query.all()
    papers = [paper_to_dict(paper, feature, feedback) for paper, feature, feedback in rows]
    if keyword_group:
        papers = [
            paper
            for paper in papers
            if keyword_group in paper.get("matched_keyword_groups", [])
        ]
    if sort_by == "date":
        papers.sort(key=lambda item: item.get("published_date") or "", reverse=True)
    elif sort_by == "created_at":
        papers.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    else:
        papers.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return papers


def latest_recommendations(db: Session) -> dict[str, object]:
    run = db.query(FetchRun).order_by(FetchRun.started_at.desc(), FetchRun.id.desc()).first()
    papers = list_paper_dicts(
        db,
        min_score=40,
        sort_by="score",
        run=run,
    )
    visible = [
        paper
        for paper in papers
        if paper["classification"] in {"Highly Relevant", "Worth Checking", "Low Priority"}
        and not paper["is_ignored"]
    ]
    return {
        "latest_fetch_run": fetch_run_to_dict(db, run) if run else None,
        "papers": visible,
    }


def fetch_run_to_dict(db: Session, run: FetchRun | None) -> dict[str, object] | None:
    if not run:
        return None
    items = (
        db.query(FetchRunItem)
        .filter(FetchRunItem.fetch_run_id == run.id)
        .order_by(FetchRunItem.id)
        .all()
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
        "papers": list_paper_dicts(db, run=run, sort_by="score"),
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


def _date_string(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_string(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

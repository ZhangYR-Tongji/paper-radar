from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.fetch import FetchCursor, FetchRun, FetchRunItem
from app.models.keyword_group import KeywordGroup
from app.models.paper import Paper
from app.models.source_config import SourceConfig
from app.schemas.fetch import ManualFetchRequest
from app.services.deduplication import find_duplicate_paper, normalize_title
from app.services.scoring import score_paper
from app.sources.arxiv_adapter import ArxivAdapter
from app.sources.base import PaperResult
from app.sources.crossref_adapter import CrossrefAdapter
from app.sources.openalex_adapter import OpenAlexAdapter
from app.sources.osf_adapter import OsfAdapter
from app.sources.semantic_scholar_adapter import SemanticScholarAdapter

ADAPTERS = {
    "arxiv": ArxivAdapter(),
    "openalex": OpenAlexAdapter(),
    "crossref": CrossrefAdapter(),
    "semantic_scholar": SemanticScholarAdapter(),
    "osf": OsfAdapter(),
}

BACKFILL_WINDOW_DAYS = 90
CURSOR_ADVANCING_MODES = {"since_last_success", "custom_range"}


def run_manual_fetch(db: Session, payload: ManualFetchRequest) -> FetchRun:
    settings = get_settings()
    running = db.query(FetchRun).filter(FetchRun.status == "running").first()
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fetch run {running.id} is already running.",
        )

    fetch_to = _ensure_utc(payload.date_to or datetime.now(UTC))
    sources_query = db.query(SourceConfig).filter(SourceConfig.is_enabled.is_(True))
    if payload.source_names:
        sources_query = sources_query.filter(SourceConfig.source_name.in_(payload.source_names))
    sources = sources_query.order_by(SourceConfig.id).all()
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先在设置中启用至少一个数据源。",
        )

    groups_query = db.query(KeywordGroup).filter(KeywordGroup.is_enabled.is_(True))
    if payload.keyword_group_ids:
        groups_query = groups_query.filter(KeywordGroup.id.in_(payload.keyword_group_ids))
    keyword_groups = groups_query.order_by(KeywordGroup.id).all()
    if not keyword_groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先在设置中创建并启用至少一个关键词组。",
        )

    run = FetchRun(
        trigger_type=payload.mode,
        status="running",
        started_at=datetime.now(UTC),
        requested_to=fetch_to,
        overlap_buffer_days=payload.overlap_buffer_days,
        enabled_sources=[source.source_name for source in sources],
        enabled_keyword_groups=[
            {"id": group.id, "name": group.name} for group in keyword_groups
        ],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    error_messages: list[str] = []
    fetch_from_values: list[datetime] = []

    for source in sources:
        adapter = ADAPTERS.get(source.source_name)
        if not adapter:
            error_messages.append(f"{source.source_name}: adapter not found")
            continue

        per_group_limit = max(source.daily_limit, 1)
        for group in keyword_groups:
            cursor = (
                _get_or_create_cursor(db, source.source_name, group.id)
                if payload.mode in CURSOR_ADVANCING_MODES
                else None
            )
            fetch_windows = _compute_fetch_windows(
                payload=payload,
                cursor=cursor,
                fetch_to=fetch_to,
                first_run_lookback_days=settings.first_run_lookback_days,
            )

            for fetch_from, window_fetch_to in fetch_windows:
                fetch_from_values.append(fetch_from)
                item = FetchRunItem(
                    fetch_run_id=run.id,
                    source_name=source.source_name,
                    keyword_group_id=group.id,
                    fetch_from=fetch_from,
                    fetch_to=window_fetch_to,
                    status="running",
                    started_at=datetime.now(UTC),
                )
                db.add(item)
                db.commit()
                db.refresh(item)

                try:
                    query = build_query(group)
                    raw_results = adapter.search(
                        query=query,
                        limit=per_group_limit,
                        date_from=fetch_from,
                        date_to=window_fetch_to,
                    )
                    filtered_results = [
                        result
                        for result in raw_results
                        if _result_in_range(result, fetch_from, window_fetch_to)
                    ]

                    counts = _store_results(db, filtered_results)

                    item.status = "success"
                    item.raw_result_count = len(raw_results)
                    item.new_paper_count = counts["new"]
                    item.duplicate_count = counts["duplicate"]
                    item.finished_at = datetime.now(UTC)

                    if cursor:
                        cursor.last_successful_until = fetch_to
                        cursor.last_run_id = run.id
                        cursor.last_status = "success"
                        cursor.last_error_message = None
                    source.last_success_at = datetime.now(UTC)
                    source.last_error_message = None

                    run.total_raw_results += len(raw_results)
                    run.total_new_papers += counts["new"]
                    run.total_duplicate_papers += counts["duplicate"]
                    run.total_scored_papers += counts["scored"]
                    run.total_highly_relevant += counts["highly_relevant"]
                    run.total_low_priority += counts["low_priority"]
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    message = f"{source.source_name} × {group.name}: {exc}"
                    error_messages.append(message)
                    item.status = "failed"
                    item.error_message = str(exc)
                    item.finished_at = datetime.now(UTC)
                    if cursor:
                        cursor.last_status = "failed"
                        cursor.last_error_message = str(exc)
                    source.last_error_at = datetime.now(UTC)
                    source.last_error_message = str(exc)
                    run.error_count += 1
                    db.commit()

    run.finished_at = datetime.now(UTC)
    run.requested_from = min(fetch_from_values) if fetch_from_values else None
    run.error_summary = "\n".join(error_messages) if error_messages else None

    if run.error_count == 0:
        run.status = "success"
    elif run.total_raw_results > 0 or run.total_new_papers > 0:
        run.status = "partial_success"
    else:
        run.status = "failed"

    db.commit()
    db.refresh(run)
    return run


def build_query(group: KeywordGroup) -> str:
    keywords = [
        *group.required_keywords,
        *group.positive_keywords,
        *group.optional_keywords,
    ]
    unique_keywords = []
    for keyword in keywords:
        cleaned = keyword.strip()
        if cleaned and cleaned not in unique_keywords:
            unique_keywords.append(cleaned)
    if not unique_keywords:
        return group.name
    return " ".join(_quote_keyword(keyword) for keyword in unique_keywords[:10])


def _quote_keyword(keyword: str) -> str:
    if " " in keyword:
        return f'"{keyword}"'
    return keyword


def _get_or_create_cursor(db: Session, source_name: str, group_id: int) -> FetchCursor:
    cursor = (
        db.query(FetchCursor)
        .filter(
            FetchCursor.source_name == source_name,
            FetchCursor.keyword_group_id == group_id,
        )
        .first()
    )
    if cursor:
        return cursor
    cursor = FetchCursor(source_name=source_name, keyword_group_id=group_id)
    db.add(cursor)
    db.flush()
    return cursor


def _compute_fetch_windows(
    payload: ManualFetchRequest,
    cursor: FetchCursor | None,
    fetch_to: datetime,
    first_run_lookback_days: int,
) -> list[tuple[datetime, datetime]]:
    if payload.mode in {"custom_range", "historical_backfill"}:
        if not payload.date_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from is required for custom range modes.",
            )
        fetch_from = _ensure_utc(payload.date_from)
        if fetch_from > fetch_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from must be earlier than date_to.",
            )
        if payload.mode == "historical_backfill":
            return _split_backfill_windows(fetch_from, fetch_to)
        return [(fetch_from, fetch_to)]

    if cursor and cursor.last_successful_until:
        fetch_from = _ensure_utc(cursor.last_successful_until) - timedelta(
            days=payload.overlap_buffer_days,
        )
    else:
        fetch_from = fetch_to - timedelta(days=first_run_lookback_days)
    return [(fetch_from, fetch_to)]


def _split_backfill_windows(
    fetch_from: datetime,
    fetch_to: datetime,
) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    current_from = fetch_from
    while current_from <= fetch_to:
        current_to = min(
            current_from + timedelta(days=BACKFILL_WINDOW_DAYS) - timedelta(microseconds=1),
            fetch_to,
        )
        windows.append((current_from, current_to))
        current_from = current_to + timedelta(microseconds=1)
    return windows


def _store_results(db: Session, filtered_results: list[PaperResult]) -> dict[str, int]:
    counts = {
        "new": 0,
        "duplicate": 0,
        "scored": 0,
        "highly_relevant": 0,
        "low_priority": 0,
    }

    for result in filtered_results:
        duplicate = find_duplicate_paper(db, result)
        if duplicate:
            counts["duplicate"] += 1
            continue

        paper = _paper_from_result(result)
        db.add(paper)
        db.flush()
        feature = score_paper(db, paper)
        counts["new"] += 1
        counts["scored"] += 1
        if feature.classification == "Highly Relevant":
            counts["highly_relevant"] += 1
        if feature.classification == "Low Priority":
            counts["low_priority"] += 1

    return counts


def _paper_from_result(result: PaperResult) -> Paper:
    doi = result.doi.lower().strip() if result.doi else None
    arxiv_id = result.arxiv_id.strip() if result.arxiv_id else None
    return Paper(
        title=result.title,
        normalized_title=normalize_title(result.title),
        abstract=result.abstract,
        authors=result.authors,
        published_date=result.published_date,
        updated_date=result.updated_date,
        source=result.source,
        source_id=result.source_id,
        doi=doi,
        arxiv_id=arxiv_id,
        url=result.url,
        pdf_url=result.pdf_url,
        venue=result.venue,
        journal=result.journal,
        conference=result.conference,
        year=result.year,
    )


def _result_in_range(result: PaperResult, date_from: datetime, date_to: datetime) -> bool:
    value = result.published_date or result.updated_date
    if not value:
        return True
    return date_from.date() <= value <= date_to.date()


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

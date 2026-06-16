from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.fetch import FetchCursor, FetchRun, FetchRunItem
from app.models.source_config import SourceConfig
from app.schemas.fetch import FetchStatusRead, ManualFetchRequest
from app.services.fetch_service import run_manual_fetch
from app.services.paper_views import fetch_run_to_dict

router = APIRouter()


@router.post("/manual")
def start_manual_fetch(
    payload: ManualFetchRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = run_manual_fetch(db, payload)
    return fetch_run_to_dict(db, run) or {}


@router.get("/status", response_model=FetchStatusRead)
def get_fetch_status(db: Session = Depends(get_db)) -> FetchStatusRead:
    run = db.query(FetchRun).filter(FetchRun.status == "running").first()
    if not run:
        return FetchStatusRead()
    return FetchStatusRead(
        is_running=True,
        current_run_id=run.id,
        message=f"Fetch run {run.id} is running.",
    )


@router.get("/runs")
def list_fetch_runs(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    runs = db.query(FetchRun).order_by(FetchRun.started_at.desc(), FetchRun.id.desc()).all()
    return [fetch_run_to_dict(db, run) or {} for run in runs]


@router.post("/runs/clear")
def clear_fetch_runs(db: Session = Depends(get_db)) -> dict[str, int]:
    running = db.query(FetchRun).filter(FetchRun.status == "running").first()
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fetch run {running.id} is still running.",
        )

    deleted_items = db.query(FetchRunItem).delete()
    deleted_cursors = db.query(FetchCursor).delete()
    deleted_runs = db.query(FetchRun).delete()
    reset_sources = 0
    for source in db.query(SourceConfig).all():
        source.last_success_at = None
        source.last_error_at = None
        source.last_error_message = None
        reset_sources += 1
    db.commit()

    return {
        "deleted_runs": deleted_runs,
        "deleted_run_items": deleted_items,
        "deleted_cursors": deleted_cursors,
        "reset_sources": reset_sources,
    }


@router.get("/runs/{run_id}")
def get_fetch_run(run_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    run = db.get(FetchRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fetch run not found")
    return fetch_run_to_dict(db, run) or {}

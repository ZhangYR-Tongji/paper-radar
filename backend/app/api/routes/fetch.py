from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.fetch import FetchRun
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


@router.get("/runs/{run_id}")
def get_fetch_run(run_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    run = db.get(FetchRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fetch run not found")
    return fetch_run_to_dict(db, run) or {}

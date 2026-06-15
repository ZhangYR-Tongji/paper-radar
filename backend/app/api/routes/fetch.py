from fastapi import APIRouter

from app.schemas.fetch import FetchStatusRead, ManualFetchRequest

router = APIRouter()


@router.post("/manual")
def start_manual_fetch(payload: ManualFetchRequest) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "message": (
            "Manual fetch flow scaffold is ready; "
            "source adapters and fetch service come next."
        ),
        "request": payload.model_dump(mode="json"),
    }


@router.get("/status", response_model=FetchStatusRead)
def get_fetch_status() -> FetchStatusRead:
    return FetchStatusRead()


@router.get("/runs")
def list_fetch_runs() -> list[dict[str, object]]:
    return []


@router.get("/runs/{run_id}")
def get_fetch_run(run_id: int) -> dict[str, object]:
    return {"id": run_id, "status": "not_implemented", "items": []}

from fastapi import APIRouter

router = APIRouter()


@router.get("/history")
def feedback_history() -> list[dict[str, object]]:
    return []

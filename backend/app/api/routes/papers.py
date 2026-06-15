from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_papers() -> list[dict[str, object]]:
    return []


@router.get("/latest")
def latest_papers() -> list[dict[str, object]]:
    return []


@router.get("/library")
def library_papers() -> list[dict[str, object]]:
    return []


@router.get("/{paper_id}")
def get_paper(paper_id: int) -> dict[str, object]:
    return {"id": paper_id, "status": "not_implemented"}


@router.post("/{paper_id}/feedback")
def create_paper_feedback(paper_id: int) -> dict[str, object]:
    return {"paper_id": paper_id, "status": "not_implemented"}


@router.put("/{paper_id}/feedback")
def update_paper_feedback(paper_id: int) -> dict[str, object]:
    return {"paper_id": paper_id, "status": "not_implemented"}

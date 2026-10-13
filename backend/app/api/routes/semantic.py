from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.semantic import SemanticSettings
from app.services.scoring import rescore_all_papers
from app.services.semantic_jobs import semantic_status, start_semantic_job

router = APIRouter()


class SemanticSettingsUpdate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    is_enabled: bool | None = None
    min_similarity: float | None = Field(default=None, ge=0.5, le=0.98)
    semantic_weight: float | None = Field(default=None, ge=0, le=1)

    @field_validator("*")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("A supplied semantic setting cannot be null.")
        return value


@router.get("/semantic")
def get_semantic_settings(db: Session = Depends(get_db)) -> dict[str, object]:
    return semantic_status(db)


@router.put("/semantic")
def update_semantic_settings(
    payload: SemanticSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    config = db.query(SemanticSettings).first()
    if not config:
        config = SemanticSettings()
        db.add(config)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    # Cached evidence is sufficient for quick threshold/toggle changes; model
    # inference is scheduled separately if any paper/profile is still missing.
    rescore_all_papers(db, compute_semantics=False)
    is_enabled = config.is_enabled
    db.commit()
    if is_enabled:
        start_semantic_job()
    return semantic_status(db)


@router.post("/semantic/prepare", status_code=status.HTTP_202_ACCEPTED)
def prepare_semantic_model(db: Session = Depends(get_db)) -> dict[str, object]:
    state = semantic_status(db)
    if not state["dependencies_ready"]:
        raise HTTPException(
            status_code=409,
            detail=(
                "请在后端环境安装本地语义依赖：python -m pip install -r requirements-semantic.txt"
            ),
        )
    start_semantic_job(prepare=True)
    return semantic_status(db)


@router.post("/semantic/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_semantics(db: Session = Depends(get_db)) -> dict[str, object]:
    if not semantic_status(db)["model_ready"]:
        raise HTTPException(status_code=409, detail="请先下载并准备本地语义模型。")
    start_semantic_job()
    return semantic_status(db)

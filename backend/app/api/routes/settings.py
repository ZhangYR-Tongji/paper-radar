from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.keyword_group import KeywordGroup
from app.models.scoring import ScoringWeights
from app.models.source_config import SourceConfig
from app.schemas.settings import (
    KeywordGroupCreate,
    KeywordGroupRead,
    KeywordGroupUpdate,
    ScoringWeightsRead,
    ScoringWeightsUpdate,
    SourceConfigRead,
    SourceConfigUpdate,
)
from app.seed import DEFAULT_KEYWORD_GROUPS

router = APIRouter()


@router.get("/sources", response_model=list[SourceConfigRead])
def list_sources(db: Session = Depends(get_db)) -> list[SourceConfig]:
    return db.query(SourceConfig).order_by(SourceConfig.id).all()


@router.put("/sources/{source_id}", response_model=SourceConfigRead)
def update_source(
    source_id: int,
    payload: SourceConfigUpdate,
    db: Session = Depends(get_db),
) -> SourceConfig:
    source = db.get(SourceConfig, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.get("/keyword-groups", response_model=list[KeywordGroupRead])
def list_keyword_groups(db: Session = Depends(get_db)) -> list[KeywordGroup]:
    return db.query(KeywordGroup).order_by(KeywordGroup.id).all()


@router.post(
    "/keyword-groups",
    response_model=KeywordGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_keyword_group(
    payload: KeywordGroupCreate,
    db: Session = Depends(get_db),
) -> KeywordGroup:
    group = KeywordGroup(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.put("/keyword-groups/{group_id}", response_model=KeywordGroupRead)
def update_keyword_group(
    group_id: int,
    payload: KeywordGroupUpdate,
    db: Session = Depends(get_db),
) -> KeywordGroup:
    group = db.get(KeywordGroup, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword group not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/keyword-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_group(group_id: int, db: Session = Depends(get_db)) -> None:
    group = db.get(KeywordGroup, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword group not found")
    db.delete(group)
    db.commit()


@router.post("/keyword-groups/reset-defaults", response_model=list[KeywordGroupRead])
def reset_keyword_group_defaults(db: Session = Depends(get_db)) -> list[KeywordGroup]:
    db.query(KeywordGroup).delete()
    for group_data in DEFAULT_KEYWORD_GROUPS:
        db.add(KeywordGroup(**group_data))
    db.commit()
    return db.query(KeywordGroup).order_by(KeywordGroup.id).all()


@router.get("/scoring-weights", response_model=ScoringWeightsRead)
def get_scoring_weights(db: Session = Depends(get_db)) -> ScoringWeights:
    weights = db.query(ScoringWeights).first()
    if not weights:
        weights = ScoringWeights()
        db.add(weights)
        db.commit()
        db.refresh(weights)
    return weights


@router.put("/scoring-weights", response_model=ScoringWeightsRead)
def update_scoring_weights(
    payload: ScoringWeightsUpdate,
    db: Session = Depends(get_db),
) -> ScoringWeights:
    weights = db.query(ScoringWeights).first()
    if not weights:
        weights = ScoringWeights()
        db.add(weights)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(weights, field, value)
    db.commit()
    db.refresh(weights)
    return weights

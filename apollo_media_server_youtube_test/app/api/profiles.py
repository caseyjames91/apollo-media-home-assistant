import uuid
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileRead

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Profile).where(Profile.name == payload.name)):
        raise HTTPException(status_code=409, detail="Profile name already exists")
    if payload.profile_type not in {"adult", "child", "managed"}:
        raise HTTPException(status_code=422, detail="Invalid profile_type")
    row = Profile(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("", response_model=list[ProfileRead])
def list_profiles(db: Session = Depends(get_db)):
    return list(db.scalars(select(Profile).order_by(Profile.name)))


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Profile, profile_id)
    if row is None: raise HTTPException(status_code=404, detail="Profile not found")
    return row


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(Profile, profile_id)
    if row is None: raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(row); db.commit()
    return Response(status_code=204)

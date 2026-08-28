from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileRead

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.post("", response_model=ProfileRead)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Profile).where(Profile.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Profile name already exists")
    row = Profile(name=payload.name, jellyfin_user_id=payload.jellyfin_user_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@router.get("", response_model=list[ProfileRead])
def list_profiles(db: Session = Depends(get_db)):
    return list(db.scalars(select(Profile).order_by(Profile.name)))

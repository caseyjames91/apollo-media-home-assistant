import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.integration import Integration
from app.models.room import Room
from app.schemas.room import RoomCreate, RoomRead, RoomUpdate


router = APIRouter(prefix="/rooms", tags=["rooms"])


def _validate_source_integration(source_integration_id: uuid.UUID | None, db: Session) -> None:
    if source_integration_id is None:
        return
    if db.get(Integration, source_integration_id) is None:
        raise HTTPException(status_code=400, detail="source integration not found")


@router.get("", response_model=list[RoomRead])
def list_rooms(db: Session = Depends(get_db)):
    return list(db.scalars(select(Room).order_by(Room.sort_order, Room.name)))


@router.post("", response_model=RoomRead, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    _validate_source_integration(payload.source_integration_id, db)
    room = Room(**payload.model_dump())
    db.add(room)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="room name already exists") from exc
    db.refresh(room)
    return room


@router.patch("/{room_id}", response_model=RoomRead)
def update_room(room_id: uuid.UUID, payload: RoomUpdate, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    changes = payload.model_dump(exclude_unset=True)
    if "source_integration_id" in changes:
        _validate_source_integration(changes["source_integration_id"], db)

    for key, value in changes.items():
        setattr(room, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="room name already exists") from exc
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=204)
def delete_room(room_id: uuid.UUID, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    from app.models.device import Device

    for device in db.scalars(select(Device).where(Device.room_id == room.id)):
        device.room_id = None

    db.delete(room)
    db.commit()
    return Response(status_code=204)

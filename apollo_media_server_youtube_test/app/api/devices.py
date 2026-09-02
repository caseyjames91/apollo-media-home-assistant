from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.device import Device
from app.schemas.device import DeviceRead, DeviceRegister

router = APIRouter(prefix="/devices", tags=["devices"])

@router.post("/register", response_model=DeviceRead)
def register_device(payload: DeviceRegister, db: Session = Depends(get_db)):
    row = db.scalar(select(Device).where(Device.device_key == payload.device_key))
    if row is None:
        row = Device(**payload.model_dump())
        db.add(row)
    else:
        row.name = payload.name
        row.device_type = payload.device_type
        row.ha_entity_id = payload.ha_entity_id
        row.kodi_jsonrpc_url = payload.kodi_jsonrpc_url
        row.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row

@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return list(db.scalars(select(Device).order_by(Device.name)))

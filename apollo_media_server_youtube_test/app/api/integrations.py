from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.integration import Integration
from app.schemas.integration import IntegrationRead, IntegrationTestResult, IntegrationUpsert
from app.services.arr import SUPPORTED_KINDS as ARR_SUPPORTED_KINDS, test_integration as test_arr_integration
from app.services.tmdb import TMDB_KIND, test_integration as test_tmdb_integration


SUPPORTED_KINDS = ARR_SUPPORTED_KINDS | {TMDB_KIND}


router = APIRouter(prefix="/integrations", tags=["integrations"])


def _read(row: Integration) -> IntegrationRead:
    return IntegrationRead(
        kind=row.kind,
        name=row.name,
        base_url=row.base_url,
        enabled=row.enabled,
        configured=bool(row.access_token),
    )


@router.get("", response_model=list[IntegrationRead])
def list_integrations(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Integration).order_by(Integration.kind, Integration.name)))
    return [_read(row) for row in rows if row.kind in SUPPORTED_KINDS]


@router.post("", response_model=IntegrationRead)
def upsert_integration(payload: IntegrationUpsert, db: Session = Depends(get_db)):
    kind = payload.kind.strip().lower()
    name = payload.name.strip() or "default"
    if kind not in SUPPORTED_KINDS:
        raise HTTPException(status_code=400, detail="kind must be radarr, sonarr, or tmdb")

    row = db.scalar(
        select(Integration).where(
            Integration.kind == kind,
            Integration.name == name,
        )
    )
    if row is None:
        # Legacy upgraded databases can still have a unique constraint on kind.
        existing_kind = db.scalar(select(Integration).where(Integration.kind == kind))
        if existing_kind is not None:
            row = existing_kind
        else:
            row = Integration(kind=kind, name=name, base_url=payload.base_url.rstrip("/"))
            db.add(row)

    row.name = name
    row.base_url = payload.base_url.rstrip("/")
    row.access_token = payload.access_token
    row.enabled = payload.enabled
    db.commit()
    db.refresh(row)
    return _read(row)


@router.post("/{kind}/{name}/test", response_model=IntegrationTestResult)
async def test_saved_integration(kind: str, name: str, db: Session = Depends(get_db)):
    row = db.scalar(
        select(Integration).where(
            Integration.kind == kind.lower(),
            Integration.name == name,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    try:
        if row.kind == TMDB_KIND:
            return await test_tmdb_integration(row)
        return await test_arr_integration(row)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{kind} connection failed: {exc}") from exc

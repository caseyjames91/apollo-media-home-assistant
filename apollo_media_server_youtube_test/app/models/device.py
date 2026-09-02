import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), default="kodi", nullable=False)
    ha_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kodi_jsonrpc_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

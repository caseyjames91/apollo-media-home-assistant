import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), default="kodi", nullable=False)

    # Legacy compatibility for existing clients.
    ha_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("integrations.id"), nullable=True
    )
    source_device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

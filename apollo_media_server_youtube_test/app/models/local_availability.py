import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class LocalAvailability(Base):
    __tablename__ = "local_availability"
    __table_args__ = (UniqueConstraint("media_id", "provider", "provider_item_id", name="uq_local_provider_item"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    media_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False)  # radarr / sonarr
    provider_item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    kodi_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    media = relationship("Media", back_populates="local_sources")

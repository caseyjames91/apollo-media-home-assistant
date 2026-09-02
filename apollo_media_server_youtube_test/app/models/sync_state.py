from datetime import datetime
import uuid
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    integration_kind: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    continue_watching_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

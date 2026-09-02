import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    profile_type: Mapped[str] = mapped_column(String(24), default="adult", nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pin_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    progress = relationship("Progress", back_populates="profile", cascade="all, delete-orphan")

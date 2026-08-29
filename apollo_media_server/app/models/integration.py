import uuid
from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_integration_kind_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # sonarr/radarr/jellyfin
    name: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

import uuid
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PathMapping(Base):
    __tablename__ = "path_mappings"
    __table_args__ = (UniqueConstraint("device_key", "source_prefix", name="uq_device_source_mapping"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_key: Mapped[str] = mapped_column(String(128), default="*", nullable=False)
    source_prefix: Mapped[str] = mapped_column(String(1000), nullable=False)
    kodi_prefix: Mapped[str] = mapped_column(String(1000), nullable=False)

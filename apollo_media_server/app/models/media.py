import uuid
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Media(Base):
    __tablename__ = "media"
    __table_args__ = (
        UniqueConstraint("media_type", "canonical_id", "season", "episode",
                         name="uq_media_canonical_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    media_type: Mapped[str] = mapped_column(String(24), nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imdb_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tmdb_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    jellyfin_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode: Mapped[int | None] = mapped_column(Integer, nullable=True)

    progress = relationship("Progress", back_populates="media", cascade="all, delete-orphan")

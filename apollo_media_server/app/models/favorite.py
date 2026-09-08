import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FavoriteItem(Base):
    __tablename__ = "favorite_items"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "media_id",
            name="uq_profile_media_favorite",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    profile = relationship(
        "Profile",
        back_populates="favorite_items",
    )
    media = relationship(
        "Media",
        back_populates="favorite_items",
    )

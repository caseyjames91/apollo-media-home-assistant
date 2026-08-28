import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    jellyfin_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    progress = relationship("Progress", back_populates="profile", cascade="all, delete-orphan")

import uuid
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ProfileIntegration(Base):
    __tablename__ = "profile_integrations"
    __table_args__ = (UniqueConstraint("profile_id", "integration_id", name="uq_profile_integration"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    integration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    external_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

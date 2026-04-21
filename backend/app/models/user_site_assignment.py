from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class UserSiteAssignment(Base):
    """Scopes inspectors and technicians to specific sites."""
    __tablename__ = "user_site_assignments"

    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    site_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="CASCADE"), primary_key=True)
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    granted_at: Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

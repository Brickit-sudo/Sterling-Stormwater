from __future__ import annotations
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class UserRole(str, enum.Enum):
    super_admin   = "super_admin"
    admin         = "admin"
    inspector     = "inspector"
    reviewer      = "reviewer"
    technician    = "technician"
    client_portal = "client_portal"


class User(Base):
    __tablename__ = "users"

    user_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:           Mapped[str]       = mapped_column(String, unique=True, nullable=False, index=True)
    name:            Mapped[str]       = mapped_column(String, nullable=False)
    hashed_password: Mapped[str]       = mapped_column(String, nullable=False)
    role:            Mapped[UserRole]  = mapped_column(SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.inspector)
    is_active:       Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    created_at:      Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

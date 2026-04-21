from __future__ import annotations
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id:  Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False, index=True)
    name:       Mapped[str]        = mapped_column(String, nullable=False)
    role:       Mapped[str | None] = mapped_column(String)   # Owner / Engineer / Inspector / etc.
    email:      Mapped[str | None] = mapped_column(String)
    phone:      Mapped[str | None] = mapped_column(String)

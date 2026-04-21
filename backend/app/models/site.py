from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("client_id", "name", name="uq_site_client_name"),
    )

    site_id:     Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id:   Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    name:        Mapped[str]        = mapped_column(String, nullable=False)
    address:     Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    created_at:  Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

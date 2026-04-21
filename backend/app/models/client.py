from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"

    client_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]       = mapped_column(String, unique=True, nullable=False, index=True)
    created_at: Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

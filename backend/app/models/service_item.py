from __future__ import annotations
import uuid
from sqlalchemy import String, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ServiceItem(Base):
    __tablename__ = "service_items"

    service_id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:               Mapped[str]          = mapped_column(String, nullable=False, unique=True, index=True)
    description:        Mapped[str | None]   = mapped_column(Text, nullable=True)
    default_unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    unit:               Mapped[str | None]   = mapped_column(String, nullable=True)   # ea, hr, ton, visit
    category:           Mapped[str | None]   = mapped_column(String, nullable=True)   # Inspection / Maintenance / JetVac / Compliance

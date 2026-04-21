from __future__ import annotations
import uuid
from datetime import date
from sqlalchemy import String, Date, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    line_item_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False, index=True)
    service_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("service_items.service_id", ondelete="SET NULL"), nullable=True)
    description:     Mapped[str]              = mapped_column(String, nullable=False)
    quantity:        Mapped[float | None]     = mapped_column(Numeric(10, 3), nullable=True)
    unit_price:      Mapped[float | None]     = mapped_column(Numeric(10, 2), nullable=True)
    amount:          Mapped[float | None]     = mapped_column(Numeric(10, 2), nullable=True)
    sort_order:      Mapped[int]              = mapped_column(Integer, nullable=False, default=0)

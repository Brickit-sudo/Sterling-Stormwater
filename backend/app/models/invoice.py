from __future__ import annotations
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="RESTRICT"), nullable=False, index=True)
    client_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False, index=True)
    quote_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.quote_id", ondelete="SET NULL"), nullable=True)
    created_by:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    invoice_number:  Mapped[str]              = mapped_column(String, nullable=False, unique=True, index=True)
    invoice_date:    Mapped[date | None]      = mapped_column(Date, nullable=True)
    due_date:        Mapped[date | None]      = mapped_column(Date, nullable=True)
    status:          Mapped[str]              = mapped_column(String, nullable=False, default="Not Paid")  # Not Paid/Paid/Partial/Void
    invoice_total:   Mapped[float | None]     = mapped_column(Numeric(10, 2), nullable=True)
    balance_due:     Mapped[float | None]     = mapped_column(Numeric(10, 2), nullable=True)
    contract_number: Mapped[str | None]       = mapped_column(String, nullable=True)
    po_number:       Mapped[str | None]       = mapped_column(String, nullable=True)
    notes:           Mapped[str | None]       = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime]         = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at:      Mapped[datetime]         = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

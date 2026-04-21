from __future__ import annotations
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    lead_id:              Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name:         Mapped[str]               = mapped_column(String, nullable=False, index=True)
    site_description:     Mapped[str | None]        = mapped_column(String, nullable=True)
    address:              Mapped[str | None]        = mapped_column(String, nullable=True)
    city:                 Mapped[str | None]        = mapped_column(String, nullable=True)
    state:                Mapped[str | None]        = mapped_column(String, nullable=True)
    zip:                  Mapped[str | None]        = mapped_column(String, nullable=True)
    property_type:        Mapped[str | None]        = mapped_column(String, nullable=True)
    managing_company:     Mapped[str | None]        = mapped_column(String, nullable=True)
    contact_name:         Mapped[str | None]        = mapped_column(String, nullable=True)
    contact_role:         Mapped[str | None]        = mapped_column(String, nullable=True)
    contact_email:        Mapped[str | None]        = mapped_column(String, nullable=True)
    contact_phone:        Mapped[str | None]        = mapped_column(String, nullable=True)
    decision_maker_type:  Mapped[str | None]        = mapped_column(String, nullable=True)
    compliance_type:      Mapped[str | None]        = mapped_column(String, nullable=True)
    observed_bmps:        Mapped[str | None]        = mapped_column(Text, nullable=True)
    permit_indicator:     Mapped[str | None]        = mapped_column(String, nullable=True)
    source_1:             Mapped[str | None]        = mapped_column(String, nullable=True)
    source_2:             Mapped[str | None]        = mapped_column(String, nullable=True)
    lead_priority:        Mapped[str | None]        = mapped_column(String, nullable=True)   # High / Medium / Low
    status:               Mapped[str]               = mapped_column(String, nullable=False, default="New")  # New/Contacted/Qualified/Converted/Dead
    notes_for_outreach:   Mapped[str | None]        = mapped_column(Text, nullable=True)
    last_verified_date:   Mapped[date | None]       = mapped_column(Date, nullable=True)
    converted_client_id:  Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    created_at:           Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_site",      "site_id"),
        Index("idx_reports_date",      "report_date"),
        Index("idx_reports_inspector", "created_by"),
    )

    report_id:        Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id:          Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="RESTRICT"), nullable=False)
    created_by:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"))
    report_type:      Mapped[str | None] = mapped_column(String)
    report_number:    Mapped[str | None] = mapped_column(String)
    inspection_date:  Mapped[str | None] = mapped_column(String)
    report_date:      Mapped[str | None] = mapped_column(String)
    prepared_by:      Mapped[str | None] = mapped_column(String)
    contract_number:  Mapped[str | None] = mapped_column(String)
    status:           Mapped[str | None] = mapped_column(String, default="Draft")
    condition_summary: Mapped[str | None] = mapped_column(String)
    session_json_path: Mapped[str | None] = mapped_column(String)
    created_at:       Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at:       Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

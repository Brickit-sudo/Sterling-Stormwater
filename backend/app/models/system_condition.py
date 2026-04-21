from __future__ import annotations
import uuid
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SystemCondition(Base):
    """Normalized per-system condition rows — replaces systems_summary_json blob."""
    __tablename__ = "system_conditions"
    __table_args__ = (
        Index("idx_syscond_report", "report_id"),
    )

    id:               Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=False)
    system_id:        Mapped[str | None] = mapped_column(String)
    system_type:      Mapped[str | None] = mapped_column(String)
    display_name:     Mapped[str | None] = mapped_column(String)
    condition:        Mapped[str | None] = mapped_column(String)   # Good / Fair / Poor / N/A
    findings:         Mapped[str | None] = mapped_column(Text)
    recommendations:  Mapped[str | None] = mapped_column(Text)

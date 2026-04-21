from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FileRecord(Base):
    """Tracks every uploaded PDF/DOCX stored in the archive folder."""
    __tablename__ = "files"
    __table_args__ = (
        Index("idx_files_site",   "site_id"),
        Index("idx_files_report", "report_id"),
    )

    file_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("sites.site_id", ondelete="RESTRICT"), nullable=False)
    report_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.report_id", ondelete="SET NULL"))
    original_name: Mapped[str]            = mapped_column(String, nullable=False)
    stored_path:   Mapped[str]            = mapped_column(String, nullable=False)
    file_hash:     Mapped[str]            = mapped_column(String, unique=True, nullable=False)  # SHA-256
    file_type:     Mapped[str]            = mapped_column(String, nullable=False)               # pdf / docx
    uploaded_by:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"))
    imported_at:   Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

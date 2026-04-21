import uuid
from datetime import datetime
from pydantic import BaseModel


class FileRecordOut(BaseModel):
    file_id: uuid.UUID
    site_id: uuid.UUID | None
    report_id: uuid.UUID | None
    original_name: str
    stored_path: str
    file_hash: str
    file_type: str
    uploaded_by: uuid.UUID | None
    imported_at: datetime

    model_config = {"from_attributes": True}


class SystemAnalysis(BaseModel):
    system_id: str
    system_type: str
    display_name: str
    findings: str
    recommendations: str
    condition: str | None = None


class ReportAnalysis(BaseModel):
    site_info: dict
    systems: list[SystemAnalysis]
    photo_captions: list[dict]
    recommendations: list[str]
    introduction: str
    sections: dict
    error: str | None = None


class UploadResponse(BaseModel):
    file: FileRecordOut
    analysis: ReportAnalysis
    is_duplicate: bool


class FileListItem(BaseModel):
    file_id: uuid.UUID
    original_name: str
    file_type: str
    imported_at: datetime
    site_name: str | None
    client_name: str | None

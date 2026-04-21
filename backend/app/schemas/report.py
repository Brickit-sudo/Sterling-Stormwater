import uuid
from datetime import datetime
from pydantic import BaseModel


class ReportOut(BaseModel):
    report_id: uuid.UUID
    site_id: uuid.UUID
    report_type: str | None
    report_number: str | None
    inspection_date: str | None
    report_date: str | None
    prepared_by: str | None
    contract_number: str | None
    status: str | None
    condition_summary: str | None
    session_json_path: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemConditionIn(BaseModel):
    system_id: str | None = None
    system_type: str | None = None
    display_name: str | None = None
    condition: str | None = None
    findings: str | None = None
    recommendations: str | None = None


class ReportUpsert(BaseModel):
    report_id: str | None = None        # omit to auto-generate
    client_name: str
    site_name: str
    site_address: str | None = None
    report_type: str | None = None
    report_number: str | None = None
    inspection_date: str | None = None
    report_date: str | None = None
    prepared_by: str | None = None
    contract_number: str | None = None
    status: str | None = "Draft"
    session_json_path: str | None = None
    systems: list[SystemConditionIn] = []


class ConditionHistoryEntry(BaseModel):
    date: str | None
    report_date: str | None
    report_type: str | None
    report_id: uuid.UUID
    system_id: str | None
    system_type: str | None
    display_name: str | None
    condition: str | None

from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class LeadCreate(BaseModel):
    company_name: str
    site_description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    property_type: Optional[str] = None
    managing_company: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    decision_maker_type: Optional[str] = None
    compliance_type: Optional[str] = None
    observed_bmps: Optional[str] = None
    permit_indicator: Optional[str] = None
    source_1: Optional[str] = None
    source_2: Optional[str] = None
    lead_priority: Optional[str] = None
    status: str = "New"
    notes_for_outreach: Optional[str] = None
    last_verified_date: Optional[date] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    site_description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    property_type: Optional[str] = None
    managing_company: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    decision_maker_type: Optional[str] = None
    compliance_type: Optional[str] = None
    observed_bmps: Optional[str] = None
    permit_indicator: Optional[str] = None
    source_1: Optional[str] = None
    source_2: Optional[str] = None
    lead_priority: Optional[str] = None
    status: Optional[str] = None
    notes_for_outreach: Optional[str] = None
    last_verified_date: Optional[date] = None
    converted_client_id: Optional[uuid.UUID] = None


class LeadOut(BaseModel):
    lead_id: uuid.UUID
    company_name: str
    site_description: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    property_type: Optional[str]
    managing_company: Optional[str]
    contact_name: Optional[str]
    contact_role: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    decision_maker_type: Optional[str]
    compliance_type: Optional[str]
    observed_bmps: Optional[str]
    permit_indicator: Optional[str]
    source_1: Optional[str]
    source_2: Optional[str]
    lead_priority: Optional[str]
    status: str
    notes_for_outreach: Optional[str]
    last_verified_date: Optional[date]
    converted_client_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}

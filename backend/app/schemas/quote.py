from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class QuoteLineItemOut(BaseModel):
    line_item_id: uuid.UUID
    quote_id: uuid.UUID
    service_item_id: Optional[uuid.UUID]
    description: str
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]
    sort_order: int

    model_config = {"from_attributes": True}


class QuoteLineItemCreate(BaseModel):
    service_item_id: Optional[uuid.UUID] = None
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class QuoteCreate(BaseModel):
    site_id: uuid.UUID
    client_id: uuid.UUID
    quote_number: Optional[str] = None
    quote_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str = "Draft"
    contract_number: Optional[str] = None
    notes: Optional[str] = None
    line_items: list[QuoteLineItemCreate] = []


class QuoteUpdate(BaseModel):
    quote_number: Optional[str] = None
    quote_date: Optional[date] = None
    expiry_date: Optional[date] = None
    sent_date: Optional[date] = None
    accepted_date: Optional[date] = None
    status: Optional[str] = None
    total_amount: Optional[float] = None
    contract_number: Optional[str] = None
    notes: Optional[str] = None


class QuoteOut(BaseModel):
    quote_id: uuid.UUID
    site_id: uuid.UUID
    client_id: uuid.UUID
    quote_number: Optional[str]
    quote_date: Optional[date]
    expiry_date: Optional[date]
    sent_date: Optional[date]
    accepted_date: Optional[date]
    status: str
    total_amount: Optional[float]
    contract_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    line_items: list[QuoteLineItemOut] = []

    model_config = {"from_attributes": True}

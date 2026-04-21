from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class InvoiceLineItemOut(BaseModel):
    line_item_id: uuid.UUID
    invoice_id: uuid.UUID
    service_item_id: Optional[uuid.UUID]
    description: str
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]
    completion_date: Optional[date]
    sort_order: int

    model_config = {"from_attributes": True}


class InvoiceLineItemCreate(BaseModel):
    service_item_id: Optional[uuid.UUID] = None
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    completion_date: Optional[date] = None
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    site_id: uuid.UUID
    client_id: uuid.UUID
    quote_id: Optional[uuid.UUID] = None
    invoice_number: str
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str = "Not Paid"
    invoice_total: Optional[float] = None
    balance_due: Optional[float] = None
    contract_number: Optional[str] = None
    po_number: Optional[str] = None
    notes: Optional[str] = None
    line_items: list[InvoiceLineItemCreate] = []


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_total: Optional[float] = None
    balance_due: Optional[float] = None
    contract_number: Optional[str] = None
    po_number: Optional[str] = None
    notes: Optional[str] = None


class InvoiceOut(BaseModel):
    invoice_id: uuid.UUID
    site_id: uuid.UUID
    client_id: uuid.UUID
    quote_id: Optional[uuid.UUID]
    invoice_number: str
    invoice_date: Optional[date]
    due_date: Optional[date]
    status: str
    invoice_total: Optional[float]
    balance_due: Optional[float]
    contract_number: Optional[str]
    po_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    line_items: list[InvoiceLineItemOut] = []

    model_config = {"from_attributes": True}


class InvoiceListOut(BaseModel):
    invoice_id: uuid.UUID
    site_id: uuid.UUID
    client_id: uuid.UUID
    invoice_number: str
    invoice_date: Optional[date]
    status: str
    invoice_total: Optional[float]
    balance_due: Optional[float]
    site_name: Optional[str] = None
    client_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

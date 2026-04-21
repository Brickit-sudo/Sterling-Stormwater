from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel


class ServiceItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_unit_price: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class ServiceItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_unit_price: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class ServiceItemOut(BaseModel):
    service_id: uuid.UUID
    name: str
    description: Optional[str]
    default_unit_price: Optional[float]
    unit: Optional[str]
    category: Optional[str]

    model_config = {"from_attributes": True}

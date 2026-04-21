import uuid
from datetime import datetime
from pydantic import BaseModel


class ClientOut(BaseModel):
    client_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SiteOut(BaseModel):
    site_id: uuid.UUID
    client_id: uuid.UUID
    name: str
    address: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SiteWithClientOut(BaseModel):
    site_id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    name: str
    address: str | None
    description: str | None
    created_at: datetime
    report_count: int

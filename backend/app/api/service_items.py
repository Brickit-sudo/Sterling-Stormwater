import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.service_item import ServiceItem
from app.models.user import User
from app.schemas.service_item import ServiceItemCreate, ServiceItemUpdate, ServiceItemOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/service-items", tags=["service-items"])


@router.get("/", response_model=list[ServiceItemOut])
async def list_service_items(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(ServiceItem).order_by(ServiceItem.category, ServiceItem.name))
    return [ServiceItemOut.model_validate(r) for r in result.scalars().all()]


@router.post("/", response_model=ServiceItemOut, status_code=201)
async def create_service_item(
    payload: ServiceItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = ServiceItem(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ServiceItemOut.model_validate(item)


@router.patch("/{service_id}", response_model=ServiceItemOut)
async def update_service_item(
    service_id: uuid.UUID,
    payload: ServiceItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(ServiceItem).where(ServiceItem.service_id == service_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return ServiceItemOut.model_validate(item)


@router.delete("/{service_id}", status_code=204)
async def delete_service_item(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(ServiceItem).where(ServiceItem.service_id == service_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Service item not found")
    await db.delete(item)
    await db.commit()

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.client import Client
from app.models.site import Site
from app.schemas.client import ClientOut, SiteOut
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=list[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Client).order_by(Client.name))
    return [ClientOut.model_validate(c) for c in result.scalars().all()]


@router.get("/{client_id}/sites", response_model=list[SiteOut])
async def list_sites_for_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Site)
        .where(Site.client_id == client_id)
        .order_by(Site.name)
    )
    return [SiteOut.model_validate(s) for s in result.scalars().all()]

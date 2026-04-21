from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.site import Site
from app.models.client import Client
from app.models.report import Report
from app.models.system_condition import SystemCondition
from app.models.user import User, UserRole
from app.models.user_site_assignment import UserSiteAssignment
from app.schemas.client import SiteWithClientOut
from app.schemas.report import ReportOut, ConditionHistoryEntry
from app.dependencies import get_current_user

router = APIRouter(prefix="/sites", tags=["sites"])


def _is_scoped(role: UserRole) -> bool:
    return role in (UserRole.inspector, UserRole.technician, UserRole.client_portal)


async def _assert_site_access(db: AsyncSession, user: User, site_id: str) -> None:
    if not _is_scoped(user.role):
        return
    result = await db.execute(
        select(UserSiteAssignment).where(
            UserSiteAssignment.site_id == site_id,
            UserSiteAssignment.user_id == user.user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Access to this site is not authorized")


@router.get("/", response_model=list[SiteWithClientOut])
async def list_sites(
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(
            Site.site_id,
            Site.client_id,
            Site.name,
            Site.address,
            Site.description,
            Site.created_at,
            Client.name.label("client_name"),
            func.count(Report.report_id).label("report_count"),
        )
        .join(Client, Site.client_id == Client.client_id)
        .outerjoin(Report, Report.site_id == Site.site_id)
        .group_by(
            Site.site_id, Site.client_id, Site.name,
            Site.address, Site.description, Site.created_at,
            Client.name,
        )
        .order_by(Client.name, Site.name)
    )

    if _is_scoped(current_user.role):
        stmt = stmt.join(
            UserSiteAssignment,
            (UserSiteAssignment.site_id == Site.site_id)
            & (UserSiteAssignment.user_id == current_user.user_id),
        )

    if search:
        stmt = stmt.where(
            Site.name.ilike(f"%{search}%") | Client.name.ilike(f"%{search}%")
        )

    rows = (await db.execute(stmt)).all()
    return [
        SiteWithClientOut(
            site_id=r.site_id,
            client_id=r.client_id,
            client_name=r.client_name,
            name=r.name,
            address=r.address,
            description=r.description,
            created_at=r.created_at,
            report_count=r.report_count,
        )
        for r in rows
    ]


@router.get("/{site_id}/reports", response_model=list[ReportOut])
async def list_reports_for_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_site_access(db, current_user, site_id)
    result = await db.execute(
        select(Report)
        .where(Report.site_id == site_id)
        .order_by(Report.report_date.desc(), Report.inspection_date.desc())
    )
    return [ReportOut.model_validate(r) for r in result.scalars().all()]


@router.get("/{site_id}/reports/count")
async def report_count_for_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_site_access(db, current_user, site_id)
    result = await db.execute(
        select(func.count()).where(Report.site_id == site_id)
    )
    return {"count": result.scalar_one()}


@router.get("/{site_id}/condition-history", response_model=list[ConditionHistoryEntry])
async def condition_history(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_site_access(db, current_user, site_id)
    result = await db.execute(
        select(
            Report.report_id,
            Report.inspection_date,
            Report.report_date,
            Report.report_type,
            SystemCondition.system_id,
            SystemCondition.system_type,
            SystemCondition.display_name,
            SystemCondition.condition,
        )
        .join(SystemCondition, SystemCondition.report_id == Report.report_id)
        .where(Report.site_id == site_id)
        .order_by(Report.report_date.asc())
    )
    return [
        ConditionHistoryEntry(
            date=r.inspection_date or r.report_date,
            report_date=r.report_date,
            report_type=r.report_type,
            report_id=r.report_id,
            system_id=r.system_id,
            system_type=r.system_type,
            display_name=r.display_name,
            condition=r.condition,
        )
        for r in result.all()
    ]

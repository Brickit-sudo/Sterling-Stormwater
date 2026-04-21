import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_db
from app.models.client import Client
from app.models.site import Site
from app.models.report import Report
from app.models.system_condition import SystemCondition
from app.models.user import User
from app.schemas.report import ReportOut, ReportUpsert
from app.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

_CONDITION_RANK = {"Poor": 0, "Fair": 1, "Good": 2, "N/A": 3}


def _worst_condition(systems: list) -> str:
    conditions = [s.condition for s in systems if s.condition]
    if not conditions:
        return "N/A"
    return min(conditions, key=lambda c: _CONDITION_RANK.get(c, 99))


async def _find_or_create_client(db: AsyncSession, name: str) -> Client:
    result = await db.execute(select(Client).where(Client.name == name))
    client = result.scalar_one_or_none()
    if not client:
        client = Client(name=name)
        db.add(client)
        await db.flush()
    return client


async def _find_or_create_site(
    db: AsyncSession, client_id: uuid.UUID, name: str, address: str | None
) -> Site:
    result = await db.execute(
        select(Site).where(Site.client_id == client_id, Site.name == name)
    )
    site = result.scalar_one_or_none()
    if not site:
        site = Site(client_id=client_id, name=name, address=address)
        db.add(site)
        await db.flush()
    elif address and not site.address:
        site.address = address
    return site


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Report).where(Report.report_id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportOut.model_validate(report)


@router.post("/", response_model=ReportOut, status_code=201)
async def upsert_report(
    body: ReportUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Find or create client
    client = await _find_or_create_client(db, body.client_name)

    # 2. Find or create site
    site = await _find_or_create_site(db, client.client_id, body.site_name, body.site_address)

    # 3. Find or create/update report
    report_id = uuid.UUID(body.report_id) if body.report_id else uuid.uuid4()
    result = await db.execute(select(Report).where(Report.report_id == report_id))
    report = result.scalar_one_or_none()

    condition_summary = _worst_condition(body.systems)

    if report:
        report.report_type     = body.report_type
        report.report_number   = body.report_number
        report.inspection_date = body.inspection_date
        report.report_date     = body.report_date
        report.prepared_by     = body.prepared_by
        report.contract_number = body.contract_number
        report.status          = body.status
        report.condition_summary = condition_summary
        report.session_json_path = body.session_json_path
    else:
        report = Report(
            report_id=report_id,
            site_id=site.site_id,
            created_by=current_user.user_id,
            report_type=body.report_type,
            report_number=body.report_number,
            inspection_date=body.inspection_date,
            report_date=body.report_date,
            prepared_by=body.prepared_by,
            contract_number=body.contract_number,
            status=body.status,
            condition_summary=condition_summary,
            session_json_path=body.session_json_path,
        )
        db.add(report)
        await db.flush()

    # 4. Replace system_conditions
    await db.execute(delete(SystemCondition).where(SystemCondition.report_id == report.report_id))
    for s in body.systems:
        db.add(SystemCondition(
            report_id=report.report_id,
            system_id=s.system_id,
            system_type=s.system_type,
            display_name=s.display_name,
            condition=s.condition,
            findings=s.findings,
            recommendations=s.recommendations,
        ))

    await db.commit()
    await db.refresh(report)
    return ReportOut.model_validate(report)

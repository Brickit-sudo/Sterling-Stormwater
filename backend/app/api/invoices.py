import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.models.site import Site
from app.models.client import Client
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceListOut, InvoiceLineItemOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/", response_model=list[InvoiceListOut])
async def list_invoices(
    status: str | None = Query(default=None),
    site_id: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(
            Invoice.invoice_id,
            Invoice.site_id,
            Invoice.client_id,
            Invoice.invoice_number,
            Invoice.invoice_date,
            Invoice.status,
            Invoice.invoice_total,
            Invoice.balance_due,
            Invoice.created_at,
            Site.name.label("site_name"),
            Client.name.label("client_name"),
        )
        .join(Site, Invoice.site_id == Site.site_id)
        .join(Client, Invoice.client_id == Client.client_id)
        .order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc())
    )
    if status:
        stmt = stmt.where(Invoice.status == status)
    if site_id:
        stmt = stmt.where(Invoice.site_id == site_id)
    if client_id:
        stmt = stmt.where(Invoice.client_id == client_id)
    if search:
        stmt = stmt.where(
            Invoice.invoice_number.ilike(f"%{search}%")
            | Site.name.ilike(f"%{search}%")
            | Client.name.ilike(f"%{search}%")
        )
    rows = (await db.execute(stmt)).all()
    return [
        InvoiceListOut(
            invoice_id=r.invoice_id,
            site_id=r.site_id,
            client_id=r.client_id,
            invoice_number=r.invoice_number,
            invoice_date=r.invoice_date,
            status=r.status,
            invoice_total=float(r.invoice_total) if r.invoice_total is not None else None,
            balance_due=float(r.balance_due) if r.balance_due is not None else None,
            site_name=r.site_name,
            client_name=r.client_name,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/summary")
async def invoice_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            func.count(Invoice.invoice_id).label("total_count"),
            func.sum(Invoice.invoice_total).label("total_billed"),
            func.sum(Invoice.balance_due).label("total_outstanding"),
        )
    )
    row = result.one()
    return {
        "total_count": row.total_count or 0,
        "total_billed": float(row.total_billed or 0),
        "total_outstanding": float(row.total_outstanding or 0),
    }


@router.post("/", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude={"line_items"})
    invoice = Invoice(**data, created_by=current_user.user_id)
    db.add(invoice)
    await db.flush()
    for i, li in enumerate(payload.line_items):
        db.add(InvoiceLineItem(invoice_id=invoice.invoice_id, sort_order=i, **li.model_dump()))
    await db.commit()
    await db.refresh(invoice)
    line_items = (await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.invoice_id).order_by(InvoiceLineItem.sort_order)
    )).scalars().all()
    out = InvoiceOut.model_validate(invoice)
    out.line_items = [InvoiceLineItemOut.model_validate(li) for li in line_items]
    return out


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.invoice_id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    line_items = (await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id).order_by(InvoiceLineItem.sort_order)
    )).scalars().all()
    out = InvoiceOut.model_validate(invoice)
    out.line_items = [InvoiceLineItemOut.model_validate(li) for li in line_items]
    return out


@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Invoice).where(Invoice.invoice_id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    await db.commit()
    await db.refresh(invoice)
    line_items = (await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id).order_by(InvoiceLineItem.sort_order)
    )).scalars().all()
    out = InvoiceOut.model_validate(invoice)
    out.line_items = [InvoiceLineItemOut.model_validate(li) for li in line_items]
    return out

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.quote import Quote
from app.models.quote_line_item import QuoteLineItem
from app.models.user import User
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteOut, QuoteLineItemOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/", response_model=list[QuoteOut])
async def list_quotes(
    site_id: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Quote).order_by(Quote.created_at.desc())
    if site_id:
        stmt = stmt.where(Quote.site_id == site_id)
    if client_id:
        stmt = stmt.where(Quote.client_id == client_id)
    if status:
        stmt = stmt.where(Quote.status == status)
    quotes = (await db.execute(stmt)).scalars().all()
    results = []
    for q in quotes:
        line_items = (await db.execute(
            select(QuoteLineItem).where(QuoteLineItem.quote_id == q.quote_id).order_by(QuoteLineItem.sort_order)
        )).scalars().all()
        out = QuoteOut.model_validate(q)
        out.line_items = [QuoteLineItemOut.model_validate(li) for li in line_items]
        results.append(out)
    return results


@router.post("/", response_model=QuoteOut, status_code=201)
async def create_quote(
    payload: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude={"line_items"})
    quote = Quote(**data, created_by=current_user.user_id)
    db.add(quote)
    await db.flush()
    for i, li in enumerate(payload.line_items):
        db.add(QuoteLineItem(quote_id=quote.quote_id, sort_order=i, **li.model_dump(exclude={"sort_order"})))
    await db.commit()
    await db.refresh(quote)
    line_items = (await db.execute(
        select(QuoteLineItem).where(QuoteLineItem.quote_id == quote.quote_id).order_by(QuoteLineItem.sort_order)
    )).scalars().all()
    out = QuoteOut.model_validate(quote)
    out.line_items = [QuoteLineItemOut.model_validate(li) for li in line_items]
    return out


@router.get("/{quote_id}", response_model=QuoteOut)
async def get_quote(
    quote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Quote).where(Quote.quote_id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    line_items = (await db.execute(
        select(QuoteLineItem).where(QuoteLineItem.quote_id == quote_id).order_by(QuoteLineItem.sort_order)
    )).scalars().all()
    out = QuoteOut.model_validate(quote)
    out.line_items = [QuoteLineItemOut.model_validate(li) for li in line_items]
    return out


@router.patch("/{quote_id}", response_model=QuoteOut)
async def update_quote(
    quote_id: uuid.UUID,
    payload: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Quote).where(Quote.quote_id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(quote, field, value)
    await db.commit()
    await db.refresh(quote)
    line_items = (await db.execute(
        select(QuoteLineItem).where(QuoteLineItem.quote_id == quote_id).order_by(QuoteLineItem.sort_order)
    )).scalars().all()
    out = QuoteOut.model_validate(quote)
    out.line_items = [QuoteLineItemOut.model_validate(li) for li in line_items]
    return out

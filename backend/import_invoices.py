"""
Import invoices from Excel into the database.
Run from backend/ directory:
    python import_invoices.py [path_to_excel]

Idempotent — skips rows where invoice_number already exists.
Also seeds the service_items catalog from unique service names found.
"""
import asyncio
import re
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load .env
from dotenv import load_dotenv
import os
load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://")

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else str(
    Path(__file__).parent.parent / "stormwater_app" / "data" / "Invoices_OneRowPerInvoice_WithBreakdown.xlsx"
)

# ── service name normalisation ────────────────────────────────────────────────
SERVICE_CATEGORY = {
    "jet": "JetVac",
    "jetvac": "JetVac",
    "vac": "JetVac",
    "inspection": "Inspection",
    "compliance": "Compliance",
    "submittal": "Compliance",
    "maintenance": "Maintenance",
    "soil filter": "Maintenance",
    "stormfilter": "Maintenance",
    "filter": "Maintenance",
    "cleaning": "Maintenance",
    "repair": "Maintenance",
    "mobilization": "Maintenance",
}

def _guess_category(name: str) -> str:
    lower = name.lower()
    for keyword, cat in SERVICE_CATEGORY.items():
        if keyword in lower:
            return cat
    return "Other"


# ── line item parser ──────────────────────────────────────────────────────────
LINE_ITEM_RE = re.compile(
    r"(?P<desc>[A-Za-z][^$\n|]{3,80?}?)\s+\$(?P<amount>[\d,]+\.?\d*)",
    re.IGNORECASE,
)
AMOUNT_RE = re.compile(r"\$\s*([\d,]+\.?\d*)")
DATE_IN_DESC_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")


def _parse_line_items(breakdown: str) -> list[dict]:
    if not isinstance(breakdown, str) or not breakdown.strip():
        return []
    items = []
    # Split on pipe, newline, or semicolon separators
    chunks = re.split(r"[|\n;]+", breakdown)
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        amounts = AMOUNT_RE.findall(chunk)
        amount = float(amounts[-1].replace(",", "")) if amounts else None
        # Strip dollar amounts from description
        desc = AMOUNT_RE.sub("", chunk).strip().strip("-–—").strip()
        desc = re.sub(r"\s{2,}", " ", desc)
        if len(desc) < 3:
            continue
        # Extract completion date if embedded
        m = DATE_IN_DESC_RE.search(desc)
        comp_date = None
        if m:
            try:
                comp_date = datetime.strptime(m.group(1), "%m/%d/%Y").date()
                desc = desc[:m.start()].strip()
            except ValueError:
                pass
        if desc:
            items.append({
                "description": desc[:255],
                "amount": amount,
                "completion_date": comp_date,
                "sort_order": i,
            })
    return items


def _parse_date(val) -> date | None:
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    s = str(val).strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


# ── DB helpers ────────────────────────────────────────────────────────────────
async def _find_or_create_client(session: AsyncSession, name: str, cache: dict):
    if name in cache:
        return cache[name]
    from app.models.client import Client
    # Upsert: insert if not exists, always return the row
    stmt = pg_insert(Client).values(name=name, created_at=datetime.utcnow(), client_id=uuid.uuid4())
    stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
    await session.execute(stmt)
    r = await session.execute(select(Client).where(Client.name == name))
    c = r.scalar_one()
    cache[name] = c
    return c


async def _find_or_create_site(session: AsyncSession, client_id, name: str, address: str | None, cache: dict):
    key = (str(client_id), name)
    if key in cache:
        return cache[key]
    from app.models.site import Site
    stmt = pg_insert(Site).values(
        site_id=uuid.uuid4(), client_id=client_id, name=name,
        address=address, created_at=datetime.utcnow()
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_site_client_name",
        set_={"address": address} if address else {"name": name},
    )
    await session.execute(stmt)
    r = await session.execute(select(Site).where(Site.client_id == client_id, Site.name == name))
    s = r.scalar_one()
    cache[key] = s
    return s


async def _find_or_create_service(session: AsyncSession, name: str, service_cache: dict):
    if name in service_cache:
        return service_cache[name]
    from app.models.service_item import ServiceItem
    stmt = pg_insert(ServiceItem).values(
        service_id=uuid.uuid4(), name=name,
        category=_guess_category(name), unit="visit"
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
    await session.execute(stmt)
    r = await session.execute(select(ServiceItem).where(ServiceItem.name == name))
    item = r.scalar_one()
    service_cache[name] = item.service_id
    return item.service_id


# ── main ──────────────────────────────────────────────────────────────────────
async def run():
    from app.models.invoice import Invoice
    from app.models.invoice_line_item import InvoiceLineItem

    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"statement_cache_size": 0})
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    df = pd.read_excel(EXCEL_PATH, sheet_name="Invoices", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    print(f"Loaded {len(df)} rows from {EXCEL_PATH}")

    # Re-read with numeric types for dollar columns
    df_num = pd.read_excel(EXCEL_PATH, sheet_name="Invoices")
    df["Invoice Total $$"] = df_num["Invoice Total $$"]
    df["Balance Due $$"] = df_num["Balance Due $$"]

    skipped = created = errors = 0
    service_cache: dict[str, uuid.UUID] = {}
    client_cache: dict[str, object] = {}
    site_cache: dict[tuple, object] = {}

    async with Session() as session:
        # Pre-load existing invoice numbers to skip efficiently
        existing_invs = set(
            r[0] for r in (await session.execute(select(Invoice.invoice_number))).all()
        )

        for idx, row in df.iterrows():
            inv_num = str(row.get("Invoice #", "")).strip()
            if not inv_num or inv_num == "nan":
                errors += 1
                continue

            if inv_num in existing_invs:
                skipped += 1
                continue

            site_name = str(row.get("Site Name", "")).strip()
            site_location = str(row.get("Site Location", "")).strip()
            if not site_name or site_name == "nan":
                errors += 1
                print(f"  Row {idx}: missing site name, skipping")
                continue

            # client = site name (invoices have no separate client column)
            client = await _find_or_create_client(session, site_name, client_cache)
            site = await _find_or_create_site(
                session, client.client_id, site_name,
                site_location if site_location != "nan" else None,
                site_cache,
            )

            contract_raw = str(row.get("Contract # / PO #", "")).strip()
            contract_num = po_num = None
            if contract_raw and contract_raw != "nan":
                if contract_raw.upper().startswith("PO"):
                    po_num = contract_raw
                else:
                    contract_num = contract_raw

            status_raw = str(row.get("Status", "")).strip()
            status = status_raw if status_raw and status_raw != "nan" else "Not Paid"

            total_val = row.get("Invoice Total $$")
            balance_val = row.get("Balance Due $$")
            total = float(total_val) if pd.notna(total_val) else None
            balance = float(balance_val) if pd.notna(balance_val) else None

            invoice = Invoice(
                site_id=site.site_id,
                client_id=client.client_id,
                invoice_number=inv_num,
                invoice_date=_parse_date(row.get("Invoice Date")),
                status=status,
                invoice_total=total,
                balance_due=balance,
                contract_number=contract_num,
                po_number=po_num,
            )
            session.add(invoice)
            await session.flush()

            # Parse and insert line items
            breakdown = row.get("Line Item Breakdown", "")
            line_items = _parse_line_items(str(breakdown) if pd.notna(breakdown) else "")
            for li in line_items:
                desc = li["description"]
                # Try to match against service catalog
                svc_id = None
                # Simple name-match: check if desc looks like a known service type
                for known in ["Annual Inspection", "JetVac Service", "Maintenance of Soil Filters",
                               "Maintenance of StormFilter", "Compliance Submittal", "Mobilization"]:
                    if known.lower() in desc.lower():
                        svc_id = await _find_or_create_service(session, known, service_cache)
                        break

                session.add(InvoiceLineItem(
                    invoice_id=invoice.invoice_id,
                    service_item_id=svc_id,
                    description=desc,
                    amount=li["amount"],
                    completion_date=li["completion_date"],
                    sort_order=li["sort_order"],
                ))

            created += 1
            if created % 50 == 0:
                await session.commit()
                print(f"  {created} invoices imported...")

        await session.commit()

    print(f"\nDone. Created: {created}  Skipped (dup): {skipped}  Errors: {errors}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())

"""
Import leads from Excel into the database.
Run from backend/ directory:
    python import_leads.py [path_to_excel]

Idempotent — skips rows where (company_name + address) already exists as a lead.
If company_name already exists as a client, marks lead as Converted automatically.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv
import os
load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://")

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else str(
    Path(__file__).parent.parent / "stormwater_app" / "data" / "Sterling Stormwater.xlsx"
)


def _str(val) -> str | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _date(val):
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    return None


async def run():
    from app.models.lead import Lead
    from app.models.client import Client

    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"statement_cache_size": 0})
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    df = pd.read_excel(EXCEL_PATH, sheet_name="2026 Leads")
    df.columns = [c.strip() for c in df.columns]
    print(f"Loaded {len(df)} rows from {EXCEL_PATH}")

    skipped = created = converted_count = 0

    async with Session() as session:
        # Pre-load all client names for fast lookup
        all_clients = (await session.execute(select(Client))).scalars().all()
        client_map = {c.name.lower(): c.client_id for c in all_clients}

        for idx, row in df.iterrows():
            company = _str(row.get("Company Name"))
            if not company:
                continue

            address = _str(row.get("Address"))

            # Dedup: skip if same company + address already in leads
            existing = await session.execute(
                select(Lead).where(Lead.company_name == company, Lead.address == address)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            # Check if already a client
            converted_client_id = client_map.get(company.lower())
            status = "Converted" if converted_client_id else "New"
            if converted_client_id:
                converted_count += 1

            zip_val = _str(row.get("ZIP"))
            if zip_val:
                # ZIP may have been read as int (e.g. 4072 instead of 04072)
                try:
                    zip_val = str(int(float(zip_val))).zfill(5)
                except (ValueError, TypeError):
                    pass

            lead = Lead(
                company_name=company,
                site_description=_str(row.get("Site Description")),
                address=address,
                city=_str(row.get("City")),
                state=_str(row.get("State")),
                zip=zip_val,
                property_type=_str(row.get("Property Type")),
                managing_company=_str(row.get("Managing Company")),
                contact_name=_str(row.get("Contact Name")),
                contact_role=_str(row.get("Contact Role")),
                contact_email=_str(row.get("Contact Email")),
                contact_phone=_str(row.get("Contact Phone")),
                decision_maker_type=_str(row.get("Decision Maker Type")),
                compliance_type=_str(row.get("Likely Compliance Type")),
                observed_bmps=_str(row.get("Observed or Documented BMPs")),
                permit_indicator=_str(row.get("Permit_or_Regulatory_Indicator")),
                source_1=_str(row.get("Source 1")),
                source_2=_str(row.get("Source 2")),
                lead_priority=_str(row.get("Lead Priority")),
                status=status,
                notes_for_outreach=_str(row.get("Notes for Outreach")),
                last_verified_date=_date(row.get("Last Verified Date")),
                converted_client_id=converted_client_id,
            )
            session.add(lead)
            created += 1

            if created % 100 == 0:
                await session.commit()
                print(f"  {created} leads imported...")

        await session.commit()

    print(f"\nDone. Created: {created}  Skipped (dup): {skipped}  Auto-converted (existing clients): {converted_count}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())

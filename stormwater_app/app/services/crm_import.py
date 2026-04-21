"""
app/services/crm_import.py
Import Monday.com CRM Excel exports → SQLite.

Usage:
    from app.services.crm_import import import_excel
    result = import_excel("contacts", "/path/to/Contacts_xxx.xlsx")
    # returns {"imported": 42, "updated": 5, "skipped": 0, "errors": []}
"""

from __future__ import annotations
import re
import datetime
from pathlib import Path

import openpyxl

from .crm_db import upsert_contact, upsert_site, upsert_lead, upsert_job, init_crm_tables


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime.datetime):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _find_header(rows: list[tuple]) -> tuple[int, list[str]]:
    """Return (index, headers) for the first row with ≥5 non-None values."""
    for i, row in enumerate(rows):
        non_null = [c for c in row if c is not None]
        if len(non_null) >= 5:
            return i, [_to_str(c) for c in row]
    return 0, []


def _is_data_row(row: tuple, n_cols: int) -> bool:
    """Return True if this row looks like a real data row (not a group header)."""
    non_null = sum(1 for c in row if c is not None)
    if non_null < 2:
        return False
    first = _to_str(row[0]) if row else ""
    # Skip rows where the first cell is a section header string (no ID-like value)
    if re.match(r"^(SS[WCO]-\d+|SWL-\d+|[A-Z][a-z])", first) or non_null >= 3:
        # Accept if looks like an ID or has enough data
        return True
    return False


def _read_rows(path: str) -> tuple[list[str], list[dict]]:
    """Return (headers, list-of-dicts) for the active sheet of an xlsx file."""
    wb   = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws   = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    hi, headers = _find_header(rows)
    if not headers:
        return [], []

    data = []
    for row in rows[hi + 1:]:
        if not any(c is not None for c in row):
            continue                           # blank row
        # Pad/trim row to header length
        padded = list(row) + [None] * max(0, len(headers) - len(row))
        padded = padded[: len(headers)]
        d = {h: padded[i] for i, h in enumerate(headers) if h}
        # Skip group-header rows (only 1-2 non-None values)
        if sum(1 for v in d.values() if v is not None) < 2:
            continue
        data.append(d)

    return headers, data


# ── Per-board importers ───────────────────────────────────────────────────────

def _import_contacts(path: str) -> dict:
    _, rows = _read_rows(path)
    imported = updated = errors = 0
    for r in rows:
        cid = _to_str(r.get("Client ID"))
        if not cid or not cid.startswith("SSC-"):
            continue
        # Skip repeated header rows from Monday group separators
        if _to_str(r.get("Name")) in ("Name","") and not _to_str(r.get("First Name")):
            continue
        try:
            upsert_contact({
                "client_id":    cid,
                "first_name":   _to_str(r.get("First Name")),
                "last_name":    _to_str(r.get("Last Name")),
                "email":        _to_str(r.get("Email")),
                "phone":        _to_str(r.get("Phone")),
                "sites_managed": _to_str(r.get("Site(s) Managed")),
                "managed_by":   _to_str(r.get("Managed By")),
                "active_status": _to_str(r.get("Active Status")),
                "account":      _to_str(r.get("Account")),
                "state":        _to_str(r.get("State")),
                "notes":        "",
            })
            imported += 1
        except Exception:
            errors += 1
    return {"imported": imported, "updated": 0, "errors": errors}


def _import_sites(path: str) -> dict:
    _, rows = _read_rows(path)
    imported = errors = 0
    for r in rows:
        sid = _to_str(r.get("Site ID"))
        if not sid or not sid.startswith("SSW-"):
            continue
        try:
            upsert_site({
                "site_id":            sid,
                "name":               _to_str(r.get("Name")),
                "address":            _to_str(r.get("Address")),
                "city":               _to_str(r.get("CITY")),
                "state":              _to_str(r.get("STATE")),
                "county":             _to_str(r.get("County")),
                "zip":                _to_str(r.get("ZIP")),
                "systems":            _to_str(r.get("Systems")),
                "contact":            _to_str(r.get("Contact")),
                "client_id":          _to_str(r.get("Client ID")),
                "managed_by":         _to_str(r.get("Managed BY")),
                "email":              _to_str(r.get("Email")),
                "phone":              _to_str(r.get("Phone")),
                "gdrive_url":         _to_str(r.get("Gdrive")),
                "service_month":      _to_str(r.get("Service Month")),
                "submittal_due_date": _to_str(r.get("Submittal Due Date")),
                "contract_start":     _to_str(r.get("Contract Term - Start")),
                "contract_end":       _to_str(r.get("Contract Term - End")),
                "budget":             _to_float(r.get("Budget")),
                "status":             _to_str(r.get("Status")),
                "notes":              _to_str(r.get("Notes")),
            })
            imported += 1
        except Exception:
            errors += 1
    return {"imported": imported, "updated": 0, "errors": errors}


def _import_leads(path: str) -> dict:
    _, rows = _read_rows(path)
    imported = errors = 0
    seen_names: set[str] = set()
    lead_counter = 1

    for r in rows:
        name = _to_str(r.get("Name"))
        if not name or name in ("Name", "Prospect", "Active", "Closed"):
            continue
        # Generate a stable lead_id from the name
        slug = re.sub(r"[^a-z0-9]", "", name.lower())[:12]
        lead_id = f"SWL-{slug[:8].upper()}{lead_counter:03d}"
        if lead_id in seen_names:
            lead_counter += 1
            lead_id = f"SWL-{slug[:8].upper()}{lead_counter:03d}"
        seen_names.add(lead_id)
        lead_counter += 1
        try:
            upsert_lead({
                "lead_id":            lead_id,
                "name":               name,
                "email":              _to_str(r.get("Email")),
                "phone":              _to_str(r.get("Phone")),
                "location":           _to_str(r.get("Location")),
                "city":               _to_str(r.get("City")),
                "state":              _to_str(r.get("State") or r.get("STATE")),
                "services":           _to_str(r.get("Services")),
                "next_activity":      _to_str(r.get("Next Activity")),
                "poc":                _to_str(r.get("POC")),
                "contact_name":       _to_str(r.get("Contact Name")),
                "gdrive_url":         _to_str(r.get("Gdrive")),
                "total_amount":       _to_float(r.get("Total")),
                "submittal_deadline": _to_str(r.get("Submittal Deadline")),
                "expires":            _to_str(r.get("Expires")),
                "notes":              "",
            })
            imported += 1
        except Exception:
            errors += 1
    return {"imported": imported, "updated": 0, "errors": errors}


def _import_jobs(path: str) -> dict:
    _, rows = _read_rows(path)
    imported = errors = 0
    job_counter = 200  # start above existing IDs
    seen: set[str] = set()

    for r in rows:
        jid = _to_str(r.get("Job ID"))
        if not jid or jid == "Job ID":
            job_counter += 1
            jid = f"SSO-{job_counter:04d}"
        if jid in seen:
            continue
        seen.add(jid)
        job_site = _to_str(r.get("Job Site"))
        if not job_site or job_site == "Job Site":
            continue
        try:
            sched = r.get("Scheduled date")
            sched_str = _to_str(sched)
            upsert_job({
                "job_id":           jid,
                "job_site":         job_site,
                "location":         _to_str(r.get("Location")),
                "job_status":       _to_str(r.get("Job Status")),
                "service":          _to_str(r.get("SERVICE")),
                "scope":            _to_str(r.get("Scope")),
                "scheduled_month":  _to_str(r.get("Scheduled Month")),
                "scheduled_date":   sched_str,
                "owner":            _to_str(r.get("Owner")),
                "quoted_amount":    _to_float(r.get("Quoted($)")),
                "actual_amount":    _to_float(r.get("Actual($)")),
                "site_id":          _to_str(r.get("Site ID")),
                "client_id":        _to_str(r.get("Client ID")),
                "lead_id":          _to_str(r.get("Lead ID")),
                "gdrive_url":       _to_str(r.get("GDrive")),
                "notes":            "",
            })
            imported += 1
        except Exception:
            errors += 1
    return {"imported": imported, "updated": 0, "errors": errors}


# ── Public entry point ────────────────────────────────────────────────────────

_IMPORTERS = {
    "contacts": _import_contacts,
    "sites":    _import_sites,
    "leads":    _import_leads,
    "jobs":     _import_jobs,
    "orders":   _import_jobs,  # alias
}


def import_excel(kind: str, path: str) -> dict:
    """
    Import a Monday.com Excel export into SQLite.
    kind: "contacts" | "sites" | "leads" | "jobs" | "orders"
    Returns {"imported": int, "errors": int}
    """
    init_crm_tables()
    fn = _IMPORTERS.get(kind.lower())
    if fn is None:
        return {"imported": 0, "errors": 1,
                "message": f"Unknown kind '{kind}'. Use: {list(_IMPORTERS)}"}
    if not Path(path).exists():
        return {"imported": 0, "errors": 1, "message": f"File not found: {path}"}

    # Temporarily disable FK enforcement so cross-table references don't block import
    from .db import get_conn
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        result = fn(path)
    finally:
        conn.execute("PRAGMA foreign_keys=ON")

    result["message"] = f"Done — {result['imported']} rows imported, {result['errors']} errors."
    return result

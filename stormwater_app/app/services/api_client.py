"""
app/services/api_client.py
HTTP client for the Sterling CRM backend.
Drop-in replacement for db.py calls — same function signatures.
Token is read from st.session_state["token"] automatically.
"""

import os
import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _headers() -> dict:
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path: str, params: dict = None) -> list | dict | None:
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", headers=_headers(), params=params,
                      timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, json: dict) -> dict | None:
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", headers=_headers(), json=json, timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Auth ─────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict | None:
    """Returns TokenResponse dict on success, None on failure."""
    return _post("/auth/login", {"email": email, "password": password})


def get_current_user() -> dict | None:
    return _get("/auth/me")


# ── Clients ──────────────────────────────────────────────────────────────────

def get_all_clients() -> list[dict]:
    return _get("/clients") or []


def get_sites_for_client(client_id: str) -> list[dict]:
    return _get(f"/clients/{client_id}/sites") or []


# ── Sites ────────────────────────────────────────────────────────────────────

def get_all_sites(search: str = "") -> list[dict]:
    """Matches db.get_all_sites() signature."""
    return _get("/sites", params={"search": search} if search else None) or []


def get_report_count_for_site(site_id: str) -> int:
    result = _get(f"/sites/{site_id}/reports/count")
    return result.get("count", 0) if result else 0


# ── Reports ──────────────────────────────────────────────────────────────────

def get_reports_for_site(site_id: str) -> list[dict]:
    """Matches db.get_reports_for_site() signature."""
    return _get(f"/sites/{site_id}/reports") or []


def get_condition_history(site_id: str) -> list[dict]:
    """Matches db.get_condition_history() signature."""
    return _get(f"/sites/{site_id}/condition-history") or []


def get_report(report_id: str) -> dict | None:
    return _get(f"/reports/{report_id}")


# ── Reports — write ───────────────────────────────────────────────────────────

# ── Invoices ─────────────────────────────────────────────────────────────────

def get_all_invoices(status: str = "", site_id: str = "", client_id: str = "", search: str = "") -> list[dict]:
    params = {}
    if status:    params["status"]    = status
    if site_id:   params["site_id"]   = site_id
    if client_id: params["client_id"] = client_id
    if search:    params["search"]    = search
    return _get("/invoices", params=params) or []


def get_invoice(invoice_id: str) -> dict | None:
    return _get(f"/invoices/{invoice_id}")


def get_invoice_summary() -> dict:
    return _get("/invoices/summary") or {"total_count": 0, "total_billed": 0, "total_outstanding": 0}


def update_invoice(invoice_id: str, data: dict) -> dict | None:
    try:
        r = httpx.patch(f"{BACKEND_URL}/invoices/{invoice_id}", headers=_headers(), json=data, timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def create_invoice(data: dict) -> dict | None:
    return _post("/invoices", data)


# ── Quotes ────────────────────────────────────────────────────────────────────

def get_all_quotes(site_id: str = "", client_id: str = "", status: str = "") -> list[dict]:
    params = {}
    if site_id:   params["site_id"]   = site_id
    if client_id: params["client_id"] = client_id
    if status:    params["status"]    = status
    return _get("/quotes", params=params) or []


def create_quote(data: dict) -> dict | None:
    return _post("/quotes", data)


def update_quote(quote_id: str, data: dict) -> dict | None:
    try:
        r = httpx.patch(f"{BACKEND_URL}/quotes/{quote_id}", headers=_headers(), json=data, timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Service Items ─────────────────────────────────────────────────────────────

def get_all_service_items() -> list[dict]:
    return _get("/service-items") or []


def create_service_item(data: dict) -> dict | None:
    return _post("/service-items", data)


def update_service_item(service_id: str, data: dict) -> dict | None:
    try:
        r = httpx.patch(f"{BACKEND_URL}/service-items/{service_id}", headers=_headers(), json=data, timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def delete_service_item(service_id: str) -> bool:
    try:
        r = httpx.delete(f"{BACKEND_URL}/service-items/{service_id}", headers=_headers(), timeout=10, follow_redirects=True)
        return r.status_code == 204
    except Exception:
        return False


# ── Prospects (backend leads from Excel import) ───────────────────────────────

def get_all_prospects(status: str = "", priority: str = "", search: str = "") -> list[dict]:
    params = {}
    if status:   params["status"]   = status
    if priority: params["priority"] = priority
    if search:   params["search"]   = search
    return _get("/leads", params=params) or []


def update_prospect(lead_id: str, data: dict) -> dict | None:
    try:
        r = httpx.patch(f"{BACKEND_URL}/leads/{lead_id}", headers=_headers(), json=data, timeout=10, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Reports — write ───────────────────────────────────────────────────────────

def upsert_report(proj) -> dict | None:
    """Sync a ProjectSession to the backend. Safe to call on every Save."""
    meta = proj.meta
    if not meta.client_name or not meta.site_name:
        return None  # not enough data to catalog yet

    systems = [
        {
            "system_id":    s.system_id,
            "system_type":  s.system_type,
            "display_name": s.display_name,
            "condition":    s.condition,
            "findings":     proj.write_ups.get(s.entry_id, {}).get("findings") if isinstance(proj.write_ups.get(s.entry_id), dict) else getattr(proj.write_ups.get(s.entry_id), "findings", None),
            "recommendations": proj.write_ups.get(s.entry_id, {}).get("recommendations") if isinstance(proj.write_ups.get(s.entry_id), dict) else getattr(proj.write_ups.get(s.entry_id), "recommendations", None),
        }
        for s in proj.systems
    ]

    payload = {
        "report_id":       proj.project_id,
        "client_name":     meta.client_name,
        "site_name":       meta.site_name,
        "site_address":    meta.site_address,
        "report_type":     meta.report_type,
        "report_number":   meta.report_number,
        "inspection_date": meta.inspection_date,
        "report_date":     meta.report_date,
        "prepared_by":     meta.prepared_by,
        "contract_number": meta.contract_number,
        "status":          meta.status,
        "session_json_path": f"projects/{proj.project_id}/session.json",
        "systems":         systems,
    }
    return _post("/reports/", payload)

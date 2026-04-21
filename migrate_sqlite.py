"""
migrate_sqlite.py
One-shot migration: reads all projects/*/session.json files and POSTs
each report to the new FastAPI backend.

Run from repo root:
    python migrate_sqlite.py

Set BACKEND_URL env var if backend is not on localhost:8000.
Set ADMIN_EMAIL / ADMIN_PASSWORD or pass via prompt.
"""

import json
import os
import sys
from pathlib import Path

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
PROJECTS_DIR = Path(__file__).parent / "stormwater_app" / "projects"


def login(email: str, password: str) -> str:
    r = httpx.post(f"{BACKEND_URL}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def upsert_report(token: str, payload: dict) -> dict:
    r = httpx.post(
        f"{BACKEND_URL}/reports/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def session_to_payload(data: dict, json_path: str) -> dict | None:
    meta = data.get("meta", {})
    client_name = meta.get("client_name", "").strip()
    site_name   = meta.get("site_name", "").strip()
    if not client_name or not site_name:
        return None

    systems = [
        {
            "system_id":   s.get("system_id"),
            "system_type": s.get("system_type"),
            "display_name": s.get("display_name"),
            "condition":   s.get("condition"),
            "findings":    data.get("write_ups", {}).get(s.get("entry_id"), {}).get("findings"),
            "recommendations": data.get("write_ups", {}).get(s.get("entry_id"), {}).get("recommendations"),
        }
        for s in data.get("systems", [])
    ]

    return {
        "report_id":       data.get("project_id"),
        "client_name":     client_name,
        "site_name":       site_name,
        "site_address":    meta.get("site_address"),
        "report_type":     meta.get("report_type"),
        "report_number":   meta.get("report_number"),
        "inspection_date": meta.get("inspection_date"),
        "report_date":     meta.get("report_date"),
        "prepared_by":     meta.get("prepared_by"),
        "contract_number": meta.get("contract_number"),
        "status":          meta.get("status", "Draft"),
        "session_json_path": json_path,
        "systems":         systems,
    }


def main():
    email    = os.environ.get("ADMIN_EMAIL") or input("Admin email: ")
    password = os.environ.get("ADMIN_PASSWORD") or input("Admin password: ")

    print(f"Logging in to {BACKEND_URL}...")
    token = login(email, password)
    print("Authenticated.")

    session_files = list(PROJECTS_DIR.glob("*/session.json"))
    print(f"Found {len(session_files)} session file(s).")

    ok = err = skip = 0
    for path in session_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            payload = session_to_payload(data, str(path))
            if payload is None:
                print(f"  SKIP  {path.parent.name}  (missing client or site name)")
                skip += 1
                continue
            upsert_report(token, payload)
            print(f"  OK    {payload['client_name']} / {payload['site_name']}  ({path.parent.name[:8]})")
            ok += 1
        except Exception as exc:
            print(f"  ERR   {path.parent.name}: {exc}")
            err += 1

    print(f"\nDone — {ok} imported, {skip} skipped, {err} errors.")


if __name__ == "__main__":
    main()

"""
app/services/sheets_sync.py
Background write-through service: SQLite → Google Sheets live sync.

Usage:
    from app.services.sheets_sync import enqueue_table, enqueue_row, start_worker

    # At app startup (app.py):
    start_worker()

    # After any CRM save:
    enqueue_table("Sites", rows)   # full overwrite of a tab
    enqueue_row("Activity Log", row)  # append a single row
"""

from __future__ import annotations
import queue
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Literal

log = logging.getLogger(__name__)

# ── Module-level singletons ───────────────────────────────────────────────────

_q: queue.Queue = queue.Queue()
_started = False
_lock = threading.Lock()

# ── Public API ────────────────────────────────────────────────────────────────

def start_worker() -> None:
    """Start the background drain thread. Safe to call multiple times — only starts once."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_drain_loop, daemon=True, name="sheets-sync-worker")
    t.start()
    log.info("Sheets sync worker started.")


def enqueue_table(tab_name: str, rows: list[dict]) -> None:
    """Queue a full-overwrite of a sheet tab. Non-blocking."""
    if not _is_configured():
        return
    # Deduplicate: if a table task for this tab is already queued, replace it
    _q.put({"op": "table", "tab": tab_name, "rows": rows, "ts": _now()})


def enqueue_row(tab_name: str, row: dict) -> None:
    """Queue an append of a single row to a sheet tab. Non-blocking."""
    if not _is_configured():
        return
    _q.put({"op": "row", "tab": tab_name, "row": row, "ts": _now()})


def push_table_now(tab_name: str, rows: list[dict]) -> bool:
    """Synchronous version — blocks until write completes. Returns True on success."""
    try:
        from app.services.google_service import load_config, sync_to_sheet
        cfg = load_config()
        url = cfg.get("sync_sheet_url") or cfg.get("sheets_crm_url", "")
        if not url:
            return False
        sync_to_sheet(url, tab_name, rows)
        return True
    except Exception as e:
        log.warning("push_table_now failed for %s: %s", tab_name, e)
        return False


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_configured() -> bool:
    try:
        from app.services.google_service import is_configured, load_config
        if not is_configured():
            return False
        cfg = load_config()
        return bool(cfg.get("sync_sheet_url") or cfg.get("sheets_crm_url"))
    except Exception:
        return False


def _get_sheet_url() -> str:
    from app.services.google_service import load_config
    cfg = load_config()
    return cfg.get("sync_sheet_url") or cfg.get("sheets_crm_url", "")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _drain_loop() -> None:
    """Drain queue in 2-second batches, deduplicate table writes, handle rate limits."""
    while True:
        pending_tables: dict[str, list[dict]] = {}   # tab_name -> latest rows
        pending_rows:   list[dict]            = []    # append tasks in order

        # Collect for up to 2 seconds
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                task = _q.get(timeout=0.1)
                if task["op"] == "table":
                    # Latest write wins — deduplicate by tab name
                    pending_tables[task["tab"]] = task["rows"]
                else:
                    pending_rows.append(task)
                _q.task_done()
            except queue.Empty:
                pass

        if not pending_tables and not pending_rows:
            continue

        url = _get_sheet_url()
        if not url:
            continue

        from app.services.google_service import sync_to_sheet, append_row_to_sheet

        # Flush table overwrites
        for tab, rows in pending_tables.items():
            _retry(lambda t=tab, r=rows: sync_to_sheet(url, t, r), tab)

        # Flush row appends
        for task in pending_rows:
            _retry(lambda t=task["tab"], r=task["row"]: append_row_to_sheet(url, t, r), task["tab"])


def _retry(fn, label: str, max_attempts: int = 3) -> None:
    """Call fn() with exponential backoff on failure."""
    for attempt in range(max_attempts):
        try:
            fn()
            return
        except Exception as e:
            wait = 2 ** attempt
            log.warning("Sheets write failed (%s) attempt %d/%d: %s — retrying in %ds",
                        label, attempt + 1, max_attempts, e, wait)
            time.sleep(wait)
    log.error("Sheets write permanently failed for tab: %s", label)


# ── CRM table sync helpers ────────────────────────────────────────────────────
# Convenience functions that pull data from SQLite and enqueue a full sync.

def sync_crm_sites() -> None:
    """Pull all crm_sites from SQLite and enqueue a full sync to 'Sites' tab."""
    try:
        from app.services.crm_db import get_all_crm_sites
        rows = get_all_crm_sites()
        enqueue_table("Sites", [dict(r) for r in rows])
    except Exception as e:
        log.warning("sync_crm_sites: %s", e)


def sync_crm_jobs() -> None:
    try:
        from app.services.crm_db import get_all_jobs
        rows = get_all_jobs()
        enqueue_table("Jobs", rows)
    except Exception as e:
        log.warning("sync_crm_jobs: %s", e)


def sync_crm_contacts() -> None:
    try:
        from app.services.crm_db import get_all_contacts
        rows = get_all_contacts()
        enqueue_table("Contacts", rows)
    except Exception as e:
        log.warning("sync_crm_contacts: %s", e)


def sync_crm_leads() -> None:
    try:
        from app.services.crm_db import get_all_leads
        rows = get_all_leads()
        enqueue_table("Leads", rows)
    except Exception as e:
        log.warning("sync_crm_leads: %s", e)


def sync_all_crm() -> None:
    """Enqueue full sync of all CRM tables."""
    sync_crm_sites()
    sync_crm_jobs()
    sync_crm_contacts()
    sync_crm_leads()

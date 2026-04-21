"""
app/services/db.py
SQLite persistence layer — Client → Site → Report hierarchy.

Runs alongside the existing JSON-per-project system (additive, never replacing).
The session.json remains the source of truth for full report data; the DB stores
only the metadata needed for listings, autocomplete, and condition trend queries.

Schema:
  clients   — one row per unique client name
  sites     — one row per (client, site) pair
  reports   — one row per saved project; mirrors key ReportMeta fields
  _meta     — internal key/value store (migration guards, schema version)
"""

import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR    = Path(__file__).parent.parent.parent   # stormwater_app/
_DB_DIR      = Path(os.environ.get("DB_DIR", str(_BASE_DIR)))
DB_PATH      = _DB_DIR / "stormwater.db"
PROJECTS_DIR = _BASE_DIR / "projects"

# ── Module-level singleton connection ─────────────────────────────────────────
_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    """Return the shared SQLite connection, creating it on first call."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
        _migrate_existing(_conn)
    return _conn


def init_db() -> None:
    """Call once at app startup to ensure schema and migration are complete."""
    get_conn()


# ── Schema ────────────────────────────────────────────────────────────────────

def _init_schema(c: sqlite3.Connection) -> None:
    c.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id   TEXT PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            created_at  TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS sites (
            site_id     TEXT PRIMARY KEY,
            client_id   TEXT NOT NULL REFERENCES clients(client_id),
            name        TEXT NOT NULL,
            address     TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at  TEXT DEFAULT (date('now')),
            UNIQUE(client_id, name)
        );

        CREATE TABLE IF NOT EXISTS reports (
            report_id            TEXT PRIMARY KEY,
            site_id              TEXT NOT NULL REFERENCES sites(site_id),
            report_type          TEXT DEFAULT 'Inspection',
            report_number        TEXT DEFAULT '',
            inspection_date      TEXT DEFAULT '',
            report_date          TEXT DEFAULT '',
            prepared_by          TEXT DEFAULT '',
            contract_number      TEXT DEFAULT '',
            status               TEXT DEFAULT 'Draft',
            condition_summary    TEXT DEFAULT '',
            systems_summary_json TEXT DEFAULT '[]',
            session_json_path    TEXT DEFAULT '',
            created_at           TEXT DEFAULT (date('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_reports_site ON reports(site_id);
        CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date);
        CREATE INDEX IF NOT EXISTS idx_sites_client ON sites(client_id);

        CREATE TABLE IF NOT EXISTS _meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    c.commit()


# ── Migration ─────────────────────────────────────────────────────────────────

def _migrate_existing(c: sqlite3.Connection) -> None:
    """
    One-time migration: scan all existing session.json files and insert them
    into the DB.  Guarded by a version flag so it only runs once.
    """
    row = c.execute("SELECT value FROM _meta WHERE key='migration_v1'").fetchone()
    if row and row["value"] == "done":
        return

    if PROJECTS_DIR.exists():
        for f in PROJECTS_DIR.glob("*/session.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                _upsert_from_raw(c, data, str(f))
            except Exception:
                pass  # skip corrupt/incomplete files silently

    c.execute("INSERT OR REPLACE INTO _meta VALUES ('migration_v1','done')")
    c.commit()


def _upsert_from_raw(c: sqlite3.Connection, data: dict, json_path: str) -> None:
    """Insert or ignore a project dict into the DB (migration helper)."""
    meta        = data.get("meta", {})
    client_name = (meta.get("client_name") or "Unknown Client").strip() or "Unknown Client"
    site_name   = (meta.get("site_name")   or "Unknown Site").strip()   or "Unknown Site"

    client_id = _make_client_id(client_name)
    c.execute("INSERT OR IGNORE INTO clients(client_id, name) VALUES (?,?)",
              (client_id, client_name))

    site_id = _make_site_id(client_name, site_name)
    c.execute("""INSERT OR IGNORE INTO sites(site_id, client_id, name, address, description)
                 VALUES (?,?,?,?,?)""",
              (site_id, client_id, site_name,
               meta.get("site_address", ""), meta.get("site_description", "")))

    systems          = data.get("systems", [])
    worst            = _worst_condition(systems)
    systems_summary  = _systems_to_json(systems)

    c.execute("""
        INSERT OR IGNORE INTO reports
          (report_id, site_id, report_type, report_number,
           inspection_date, report_date, prepared_by, contract_number,
           status, condition_summary, systems_summary_json, session_json_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("project_id", str(uuid.uuid4())),
        site_id,
        meta.get("report_type", "Inspection"),
        meta.get("report_number", ""),
        meta.get("inspection_date", ""),
        meta.get("report_date", ""),
        meta.get("prepared_by", ""),
        meta.get("contract_number", ""),
        meta.get("status", "Draft"),
        worst,
        systems_summary,
        json_path,
    ))


# ── Public write operations ───────────────────────────────────────────────────

def upsert_report(proj) -> None:
    """
    Sync a ProjectSession into the DB after save_project_json() completes.
    Safe to call on every save — uses INSERT OR REPLACE.
    """
    meta        = proj.meta
    client_name = (meta.client_name or "Unknown Client").strip() or "Unknown Client"
    site_name   = (meta.site_name   or "Unknown Site").strip()   or "Unknown Site"

    c = get_conn()

    client_id = _make_client_id(client_name)
    c.execute("INSERT OR IGNORE INTO clients(client_id, name) VALUES (?,?)",
              (client_id, client_name))
    c.execute("UPDATE clients SET name=? WHERE client_id=?", (client_name, client_id))

    site_id = _make_site_id(client_name, site_name)
    c.execute("""INSERT OR IGNORE INTO sites(site_id, client_id, name, address, description)
                 VALUES (?,?,?,?,?)""",
              (site_id, client_id, site_name,
               meta.site_address or "", meta.site_description or ""))
    c.execute("""UPDATE sites SET name=?, address=?, description=? WHERE site_id=?""",
              (site_name, meta.site_address or "", meta.site_description or "", site_id))

    worst           = _worst_condition([{"condition": s.condition} for s in proj.systems])
    systems_summary = _systems_to_json([
        {"system_id": s.system_id, "system_type": s.system_type,
         "display_name": s.display_name, "condition": s.condition}
        for s in proj.systems
    ])
    json_path = str(PROJECTS_DIR / proj.project_id / "session.json")

    c.execute("""
        INSERT OR REPLACE INTO reports
          (report_id, site_id, report_type, report_number,
           inspection_date, report_date, prepared_by, contract_number,
           status, condition_summary, systems_summary_json, session_json_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        proj.project_id, site_id,
        meta.report_type, meta.report_number or "",
        meta.inspection_date or "", meta.report_date or "",
        meta.prepared_by or "", meta.contract_number or "",
        meta.status, worst, systems_summary, json_path,
    ))
    c.commit()


# ── Public read operations ────────────────────────────────────────────────────

def get_all_clients() -> list[dict]:
    c = get_conn()
    rows = c.execute("SELECT client_id, name FROM clients ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_all_sites(search: str = "") -> list[dict]:
    """
    Return all sites with their client name and report count.
    Optional ``search`` filters by site name or client name (case-insensitive).
    Each row: {site_id, site_name, client_name, address, report_count}
    """
    c = get_conn()
    rows = c.execute("""
        SELECT s.site_id, s.name AS site_name, s.address,
               cl.name AS client_name,
               COUNT(r.report_id) AS report_count
        FROM sites s
        JOIN clients cl ON cl.client_id = s.client_id
        LEFT JOIN reports r ON r.site_id = s.site_id
        GROUP BY s.site_id
        ORDER BY cl.name, s.name
    """).fetchall()
    results = [dict(r) for r in rows]
    if search:
        q = search.strip().lower()
        results = [
            r for r in results
            if q in r["site_name"].lower() or q in r["client_name"].lower()
        ]
    return results


def get_sites_for_client(client_id: str) -> list[dict]:
    c = get_conn()
    rows = c.execute(
        "SELECT site_id, name, address FROM sites WHERE client_id=? ORDER BY name",
        (client_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_reports_for_site(site_id: str) -> list[dict]:
    c = get_conn()
    rows = c.execute("""
        SELECT report_id, report_type, report_number, inspection_date, report_date,
               prepared_by, status, condition_summary, systems_summary_json, session_json_path
        FROM reports
        WHERE site_id=?
        ORDER BY report_date DESC, inspection_date DESC
    """, (site_id,)).fetchall()
    return [dict(r) for r in rows]


def get_site_for_project(client_name: str, site_name: str) -> Optional[dict]:
    """Return the site row for a (client_name, site_name) pair, or None."""
    if not client_name or not site_name:
        return None
    site_id = _make_site_id(client_name, site_name)
    c = get_conn()
    row = c.execute(
        "SELECT site_id, client_id, name, address FROM sites WHERE site_id=?",
        (site_id,),
    ).fetchone()
    return dict(row) if row else None


def get_condition_history(site_id: str) -> list[dict]:
    """
    Return condition history for all BMPs at a site, across all reports.
    Each entry: {date, report_type, system_id, system_type, display_name, condition}
    """
    rows    = get_reports_for_site(site_id)
    history = []
    for row in rows:
        date = row.get("inspection_date") or row.get("report_date") or ""
        try:
            systems = json.loads(row.get("systems_summary_json") or "[]")
        except Exception:
            systems = []
        for s in systems:
            history.append({
                "date":         date,
                "report_date":  row.get("report_date", ""),
                "report_type":  row.get("report_type", ""),
                "report_id":    row.get("report_id", ""),
                "system_id":    s.get("system_id", ""),
                "system_type":  s.get("system_type", ""),
                "display_name": s.get("display_name", ""),
                "condition":    s.get("condition", "N/A"),
            })
    return history


def get_report_count_for_site(client_name: str, site_name: str) -> int:
    """Quick count of reports at a site — used for setup page hints."""
    site = get_site_for_project(client_name, site_name)
    if not site:
        return 0
    c = get_conn()
    row = c.execute(
        "SELECT COUNT(*) as n FROM reports WHERE site_id=?", (site["site_id"],)
    ).fetchone()
    return row["n"] if row else 0


# ── Private helpers ───────────────────────────────────────────────────────────

def _make_client_id(client_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, client_name.strip().lower()))


def _make_site_id(client_name: str, site_name: str) -> str:
    key = f"{client_name.strip().lower()}|{site_name.strip().lower()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


_COND_RANK = {"Poor": 0, "Fair": 1, "Good": 2, "N/A": 3}


def _worst_condition(systems: list[dict]) -> str:
    if not systems:
        return "N/A"
    return min(
        (s.get("condition", "Good") for s in systems),
        key=lambda c: _COND_RANK.get(c, 2),
        default="N/A",
    )


def _systems_to_json(systems: list[dict]) -> str:
    return json.dumps([
        {
            "system_id":   s.get("system_id", ""),
            "system_type": s.get("system_type", ""),
            "display_name": s.get("display_name", ""),
            "condition":   s.get("condition", "N/A"),
        }
        for s in systems
    ])


# ── Local auth (no backend required) ─────────────────────────────────────────

def _ensure_local_users(c: sqlite3.Connection) -> None:
    c.execute("""CREATE TABLE IF NOT EXISTS local_users (
        email TEXT PRIMARY KEY,
        name  TEXT DEFAULT '',
        salt  TEXT NOT NULL,
        hash  TEXT NOT NULL
    )""")
    c.commit()


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def init_local_user(email: str, password: str, name: str = "") -> None:
    """Seed a local user if they don't exist yet."""
    c = get_conn()
    _ensure_local_users(c)
    if c.execute("SELECT 1 FROM local_users WHERE email=?", (email,)).fetchone():
        return
    salt = secrets.token_hex(16)
    c.execute(
        "INSERT INTO local_users(email, name, salt, hash) VALUES (?,?,?,?)",
        (email, name or email.split("@")[0], salt, _hash_pw(password, salt)),
    )
    c.commit()


def local_login(email: str, password: str) -> bool:
    """Return True if email + password match the local user record."""
    c = get_conn()
    try:
        _ensure_local_users(c)
        row = c.execute(
            "SELECT salt, hash FROM local_users WHERE email=?", (email,)
        ).fetchone()
    except Exception:
        return False
    if not row:
        return False
    return _hash_pw(password, row["salt"]) == row["hash"]


def set_local_password(email: str, new_password: str) -> bool:
    """Update the local password for an existing user. Returns False if user not found."""
    c = get_conn()
    try:
        _ensure_local_users(c)
        if not c.execute("SELECT 1 FROM local_users WHERE email=?", (email,)).fetchone():
            return False
        salt = secrets.token_hex(16)
        c.execute(
            "UPDATE local_users SET salt=?, hash=? WHERE email=?",
            (salt, _hash_pw(new_password, salt), email),
        )
        c.commit()
        return True
    except Exception:
        return False

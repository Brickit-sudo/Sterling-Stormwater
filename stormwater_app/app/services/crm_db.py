"""
app/services/crm_db.py
CRM tables and CRUD — additive to the existing db.py report schema.

Tables (crm_ prefix avoids collision with report-workflow tables):
  crm_contacts  — Monday Contacts board  (SSC-XXXX)
  crm_sites     — Monday Site Information (SSW-XXXX)
  crm_leads     — Monday Leads board      (SWL-XXXX)
  crm_jobs      — Monday Orders board     (SSO-XXXX)
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from .db import get_conn

_SEED_PATH = Path(__file__).parent.parent.parent / "data" / "crm_seed.json"


# ── Schema init ───────────────────────────────────────────────────────────────

def init_crm_tables() -> None:
    c = get_conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS crm_contacts (
            client_id     TEXT PRIMARY KEY,
            first_name    TEXT,
            last_name     TEXT,
            email         TEXT,
            phone         TEXT,
            sites_managed TEXT,
            managed_by    TEXT,
            active_status TEXT,
            account       TEXT,
            state         TEXT,
            notes         TEXT,
            updated_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS crm_sites (
            site_id            TEXT PRIMARY KEY,
            name               TEXT NOT NULL,
            address            TEXT,
            city               TEXT,
            state              TEXT,
            county             TEXT,
            zip                TEXT,
            systems            TEXT,
            contact            TEXT,
            client_id          TEXT REFERENCES crm_contacts(client_id),
            managed_by         TEXT,
            email              TEXT,
            phone              TEXT,
            gdrive_url         TEXT,
            service_month      TEXT,
            submittal_due_date TEXT,
            contract_start     TEXT,
            contract_end       TEXT,
            budget             REAL,
            status             TEXT,
            notes              TEXT,
            updated_at         TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_sites_client ON crm_sites(client_id);
        CREATE INDEX IF NOT EXISTS idx_crm_sites_state  ON crm_sites(state);

        CREATE TABLE IF NOT EXISTS crm_leads (
            lead_id            TEXT PRIMARY KEY,
            name               TEXT NOT NULL,
            email              TEXT,
            phone              TEXT,
            location           TEXT,
            city               TEXT,
            state              TEXT,
            services           TEXT,
            next_activity      TEXT,
            poc                TEXT,
            contact_name       TEXT,
            gdrive_url         TEXT,
            total_amount       REAL,
            submittal_deadline TEXT,
            expires            TEXT,
            notes              TEXT,
            updated_at         TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_leads_activity ON crm_leads(next_activity);

        CREATE TABLE IF NOT EXISTS crm_jobs (
            job_id          TEXT PRIMARY KEY,
            job_site        TEXT,
            location        TEXT,
            job_status      TEXT,
            service         TEXT,
            scope           TEXT,
            scheduled_month TEXT,
            scheduled_date  TEXT,
            owner           TEXT,
            quoted_amount   REAL,
            actual_amount   REAL,
            site_id         TEXT REFERENCES crm_sites(site_id),
            client_id       TEXT REFERENCES crm_contacts(client_id),
            lead_id         TEXT REFERENCES crm_leads(lead_id),
            gdrive_url      TEXT,
            notes           TEXT,
            updated_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_jobs_site   ON crm_jobs(site_id);
        CREATE INDEX IF NOT EXISTS idx_crm_jobs_status ON crm_jobs(job_status);
        CREATE INDEX IF NOT EXISTS idx_crm_jobs_owner  ON crm_jobs(owner);
        CREATE INDEX IF NOT EXISTS idx_crm_jobs_month  ON crm_jobs(scheduled_month);

        CREATE TABLE IF NOT EXISTS crm_communications (
            comm_id        TEXT PRIMARY KEY,
            entity_type    TEXT NOT NULL,
            entity_id      TEXT NOT NULL,
            entity_name    TEXT,
            type           TEXT NOT NULL DEFAULT 'note',
            direction      TEXT DEFAULT 'outbound',
            subject        TEXT,
            body           TEXT,
            attachment_url TEXT,
            created_by     TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_crm_comm_entity  ON crm_communications(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_crm_comm_type    ON crm_communications(type);
        CREATE INDEX IF NOT EXISTS idx_crm_comm_created ON crm_communications(created_at DESC);
    """)
    c.commit()
    _seed_if_empty(c)


def _seed_if_empty(c: sqlite3.Connection) -> None:
    if not _SEED_PATH.exists():
        return
    data = json.loads(_SEED_PATH.read_text())
    seed_count = len(data.get("crm_sites", []))
    db_count = c.execute("SELECT COUNT(*) FROM crm_sites").fetchone()[0]
    if db_count >= seed_count:
        return
    table_cols = {
        "crm_contacts": ["client_id","first_name","last_name","email","phone","sites_managed","managed_by","active_status","account","state","notes"],
        "crm_sites": ["site_id","name","address","city","state","county","zip","systems","contact","client_id","managed_by","email","phone","gdrive_url","service_month","submittal_due_date","contract_start","contract_end","budget","status","notes"],
        "crm_leads": ["lead_id","name","email","phone","location","city","state","services","next_activity","poc","contact_name","gdrive_url","total_amount","submittal_deadline","expires","notes"],
        "crm_jobs": ["job_id","job_site","location","job_status","service","scope","scheduled_month","scheduled_date","owner","quoted_amount","actual_amount","site_id","client_id","lead_id","gdrive_url","notes"],
    }
    c.execute("PRAGMA foreign_keys = OFF")
    for table, cols in table_cols.items():
        rows = data.get(table, [])
        if not rows:
            continue
        placeholders = ",".join("?" * len(cols))
        col_list = ",".join(cols)
        c.executemany(
            f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})",
            [[r.get(col) for col in cols] for r in rows],
        )
    c.execute("PRAGMA foreign_keys = ON")
    c.commit()


# ── Upsert helpers ────────────────────────────────────────────────────────────

def upsert_contact(d: dict) -> None:
    c = get_conn()
    c.execute("""
        INSERT INTO crm_contacts
          (client_id, first_name, last_name, email, phone,
           sites_managed, managed_by, active_status, account, state, notes)
        VALUES (:client_id,:first_name,:last_name,:email,:phone,
                :sites_managed,:managed_by,:active_status,:account,:state,:notes)
        ON CONFLICT(client_id) DO UPDATE SET
          first_name=excluded.first_name, last_name=excluded.last_name,
          email=COALESCE(excluded.email, crm_contacts.email),
          phone=COALESCE(excluded.phone, crm_contacts.phone),
          sites_managed=excluded.sites_managed, managed_by=excluded.managed_by,
          active_status=excluded.active_status, account=excluded.account,
          state=excluded.state,
          notes=COALESCE(crm_contacts.notes, excluded.notes),
          updated_at=datetime('now')
    """, {k: d.get(k) for k in
          ["client_id","first_name","last_name","email","phone",
           "sites_managed","managed_by","active_status","account","state","notes"]})
    c.commit()


def upsert_site(d: dict) -> None:
    c = get_conn()
    c.execute("""
        INSERT INTO crm_sites
          (site_id, name, address, city, state, county, zip, systems, contact,
           client_id, managed_by, email, phone, gdrive_url, service_month,
           submittal_due_date, contract_start, contract_end, budget, status, notes)
        VALUES (:site_id,:name,:address,:city,:state,:county,:zip,:systems,:contact,
                :client_id,:managed_by,:email,:phone,:gdrive_url,:service_month,
                :submittal_due_date,:contract_start,:contract_end,:budget,:status,:notes)
        ON CONFLICT(site_id) DO UPDATE SET
          name=excluded.name, address=excluded.address, city=excluded.city,
          state=excluded.state, county=excluded.county, zip=excluded.zip,
          systems=excluded.systems, contact=excluded.contact,
          client_id=excluded.client_id, managed_by=excluded.managed_by,
          email=COALESCE(excluded.email, crm_sites.email),
          phone=COALESCE(excluded.phone, crm_sites.phone),
          gdrive_url=COALESCE(excluded.gdrive_url, crm_sites.gdrive_url),
          service_month=excluded.service_month,
          submittal_due_date=excluded.submittal_due_date,
          contract_start=excluded.contract_start, contract_end=excluded.contract_end,
          budget=COALESCE(excluded.budget, crm_sites.budget),
          status=excluded.status,
          notes=COALESCE(crm_sites.notes, excluded.notes),
          updated_at=datetime('now')
    """, {k: d.get(k) for k in
          ["site_id","name","address","city","state","county","zip","systems","contact",
           "client_id","managed_by","email","phone","gdrive_url","service_month",
           "submittal_due_date","contract_start","contract_end","budget","status","notes"]})
    c.commit()


def upsert_lead(d: dict) -> None:
    c = get_conn()
    c.execute("""
        INSERT INTO crm_leads
          (lead_id, name, email, phone, location, city, state, services,
           next_activity, poc, contact_name, gdrive_url, total_amount,
           submittal_deadline, expires, notes)
        VALUES (:lead_id,:name,:email,:phone,:location,:city,:state,:services,
                :next_activity,:poc,:contact_name,:gdrive_url,:total_amount,
                :submittal_deadline,:expires,:notes)
        ON CONFLICT(lead_id) DO UPDATE SET
          name=excluded.name,
          email=COALESCE(excluded.email, crm_leads.email),
          phone=COALESCE(excluded.phone, crm_leads.phone),
          location=excluded.location, city=excluded.city, state=excluded.state,
          services=excluded.services, next_activity=excluded.next_activity,
          poc=excluded.poc, contact_name=excluded.contact_name,
          gdrive_url=COALESCE(excluded.gdrive_url, crm_leads.gdrive_url),
          total_amount=COALESCE(excluded.total_amount, crm_leads.total_amount),
          submittal_deadline=excluded.submittal_deadline, expires=excluded.expires,
          notes=COALESCE(crm_leads.notes, excluded.notes),
          updated_at=datetime('now')
    """, {k: d.get(k) for k in
          ["lead_id","name","email","phone","location","city","state","services",
           "next_activity","poc","contact_name","gdrive_url","total_amount",
           "submittal_deadline","expires","notes"]})
    c.commit()


def upsert_job(d: dict) -> None:
    c = get_conn()
    c.execute("""
        INSERT INTO crm_jobs
          (job_id, job_site, location, job_status, service, scope,
           scheduled_month, scheduled_date, owner, quoted_amount, actual_amount,
           site_id, client_id, lead_id, gdrive_url, notes)
        VALUES (:job_id,:job_site,:location,:job_status,:service,:scope,
                :scheduled_month,:scheduled_date,:owner,:quoted_amount,:actual_amount,
                :site_id,:client_id,:lead_id,:gdrive_url,:notes)
        ON CONFLICT(job_id) DO UPDATE SET
          job_site=excluded.job_site, location=excluded.location,
          job_status=excluded.job_status, service=excluded.service,
          scope=excluded.scope, scheduled_month=excluded.scheduled_month,
          scheduled_date=excluded.scheduled_date, owner=excluded.owner,
          quoted_amount=COALESCE(excluded.quoted_amount, crm_jobs.quoted_amount),
          actual_amount=COALESCE(excluded.actual_amount, crm_jobs.actual_amount),
          site_id=excluded.site_id, client_id=excluded.client_id,
          lead_id=excluded.lead_id,
          gdrive_url=COALESCE(excluded.gdrive_url, crm_jobs.gdrive_url),
          notes=COALESCE(crm_jobs.notes, excluded.notes),
          updated_at=datetime('now')
    """, {k: d.get(k) for k in
          ["job_id","job_site","location","job_status","service","scope",
           "scheduled_month","scheduled_date","owner","quoted_amount","actual_amount",
           "site_id","client_id","lead_id","gdrive_url","notes"]})
    c.commit()


# ── Read operations ───────────────────────────────────────────────────────────

def get_all_contacts(search: str = "", status: str = "") -> list[dict]:
    c = get_conn()
    sql  = "SELECT * FROM crm_contacts WHERE 1=1"
    args: list = []
    if search:
        sql  += " AND (first_name||' '||last_name LIKE ? OR email LIKE ? OR account LIKE ?)"
        q     = f"%{search}%"
        args += [q, q, q]
    if status:
        sql  += " AND active_status=?"
        args.append(status)
    sql += " ORDER BY last_name, first_name"
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def get_all_crm_sites(search: str = "", state: str = "") -> list[dict]:
    c = get_conn()
    sql  = """
        SELECT s.*, c.first_name||' '||c.last_name AS contact_full_name, c.email AS contact_email
        FROM crm_sites s
        LEFT JOIN crm_contacts c ON c.client_id = s.client_id
        WHERE 1=1
    """
    args: list = []
    if search:
        sql  += " AND (s.name LIKE ? OR s.city LIKE ? OR s.managed_by LIKE ?)"
        q     = f"%{search}%"
        args += [q, q, q]
    if state:
        sql  += " AND s.state=?"
        args.append(state)
    sql += " ORDER BY s.name"
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def get_all_jobs(status: str = "", owner: str = "", month: str = "",
                 search: str = "") -> list[dict]:
    c = get_conn()
    sql  = "SELECT * FROM crm_jobs WHERE 1=1"
    args: list = []
    if status:
        sql  += " AND job_status=?"
        args.append(status)
    if owner:
        sql  += " AND owner LIKE ?"
        args.append(f"%{owner}%")
    if month:
        sql  += " AND scheduled_month=?"
        args.append(month)
    if search:
        sql  += " AND (job_site LIKE ? OR service LIKE ?)"
        q     = f"%{search}%"
        args += [q, q]
    sql += " ORDER BY scheduled_date DESC, job_site"
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def get_all_leads(next_activity: str = "", state: str = "",
                  search: str = "") -> list[dict]:
    c = get_conn()
    sql  = "SELECT * FROM crm_leads WHERE 1=1"
    args: list = []
    if next_activity:
        sql  += " AND next_activity=?"
        args.append(next_activity)
    if state:
        sql  += " AND state=?"
        args.append(state)
    if search:
        sql  += " AND (name LIKE ? OR email LIKE ? OR contact_name LIKE ?)"
        q     = f"%{search}%"
        args += [q, q, q]
    sql += " ORDER BY name"
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def get_jobs_for_site(site_id: str) -> list[dict]:
    c = get_conn()
    rows = c.execute(
        "SELECT * FROM crm_jobs WHERE site_id=? ORDER BY scheduled_date DESC",
        (site_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_crm_stats() -> dict:
    c = get_conn()
    return {
        "sites":    c.execute("SELECT COUNT(*) FROM crm_sites").fetchone()[0],
        "contacts": c.execute("SELECT COUNT(*) FROM crm_contacts").fetchone()[0],
        "jobs":     c.execute("SELECT COUNT(*) FROM crm_jobs").fetchone()[0],
        "leads":    c.execute("SELECT COUNT(*) FROM crm_leads").fetchone()[0],
        "open_jobs": c.execute(
            "SELECT COUNT(*) FROM crm_jobs WHERE job_status != 'Complete'"
        ).fetchone()[0],
        "active_contacts": c.execute(
            "SELECT COUNT(*) FROM crm_contacts WHERE active_status='Active'"
        ).fetchone()[0],
        "quoted_total": c.execute(
            "SELECT COALESCE(SUM(quoted_amount),0) FROM crm_jobs WHERE job_status != 'Complete'"
        ).fetchone()[0],
    }


# ── Delete operations ─────────────────────────────────────────────────────────

def delete_contact(client_id: str) -> None:
    c = get_conn()
    c.execute("DELETE FROM crm_contacts WHERE client_id=?", (client_id,))
    c.commit()


def delete_site(site_id: str) -> None:
    c = get_conn()
    c.execute("DELETE FROM crm_sites WHERE site_id=?", (site_id,))
    c.commit()


def delete_job(job_id: str) -> None:
    c = get_conn()
    c.execute("DELETE FROM crm_jobs WHERE job_id=?", (job_id,))
    c.commit()


def delete_lead(lead_id: str) -> None:
    c = get_conn()
    c.execute("DELETE FROM crm_leads WHERE lead_id=?", (lead_id,))
    c.commit()


# ── Distinct value helpers (for filter dropdowns) ─────────────────────────────

def get_job_statuses() -> list[str]:
    c = get_conn()
    rows = c.execute(
        "SELECT DISTINCT job_status FROM crm_jobs WHERE job_status IS NOT NULL ORDER BY job_status"
    ).fetchall()
    return [r[0] for r in rows]


def get_job_owners() -> list[str]:
    c = get_conn()
    rows = c.execute(
        "SELECT DISTINCT owner FROM crm_jobs WHERE owner IS NOT NULL ORDER BY owner"
    ).fetchall()
    return [r[0] for r in rows]


def get_job_months() -> list[str]:
    _ORDER = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    c = get_conn()
    rows = c.execute(
        "SELECT DISTINCT scheduled_month FROM crm_jobs WHERE scheduled_month IS NOT NULL"
    ).fetchall()
    found = {r[0] for r in rows}
    return [m for m in _ORDER if m in found]


def get_lead_activities() -> list[str]:
    c = get_conn()
    rows = c.execute(
        "SELECT DISTINCT next_activity FROM crm_leads WHERE next_activity IS NOT NULL ORDER BY next_activity"
    ).fetchall()
    return [r[0] for r in rows]


# ── Communications CRUD ───────────────────────────────────────────────────────

def upsert_communication(d: dict) -> None:
    c = get_conn()
    c.execute("""
        INSERT INTO crm_communications
          (comm_id, entity_type, entity_id, entity_name, type, direction,
           subject, body, attachment_url, created_by, created_at)
        VALUES (:comm_id,:entity_type,:entity_id,:entity_name,:type,:direction,
                :subject,:body,:attachment_url,:created_by,
                COALESCE(:created_at, datetime('now')))
        ON CONFLICT(comm_id) DO UPDATE SET
          entity_name=excluded.entity_name, type=excluded.type,
          direction=excluded.direction, subject=excluded.subject,
          body=excluded.body,
          attachment_url=COALESCE(excluded.attachment_url, crm_communications.attachment_url),
          created_by=excluded.created_by
    """, {k: d.get(k) for k in
          ["comm_id","entity_type","entity_id","entity_name","type","direction",
           "subject","body","attachment_url","created_by","created_at"]})
    c.commit()


def get_communications(entity_type: str = "", entity_id: str = "",
                       comm_type: str = "", search: str = "",
                       limit: int = 100) -> list[dict]:
    c = get_conn()
    sql  = "SELECT * FROM crm_communications WHERE 1=1"
    args: list = []
    if entity_type:
        sql  += " AND entity_type=?"
        args.append(entity_type)
    if entity_id:
        sql  += " AND entity_id=?"
        args.append(entity_id)
    if comm_type:
        sql  += " AND type=?"
        args.append(comm_type)
    if search:
        sql  += " AND (subject LIKE ? OR body LIKE ? OR entity_name LIKE ?)"
        q     = f"%{search}%"
        args += [q, q, q]
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def delete_communication(comm_id: str) -> None:
    c = get_conn()
    c.execute("DELETE FROM crm_communications WHERE comm_id=?", (comm_id,))
    c.commit()


# ── Analytics / Dashboard helpers ────────────────────────────────────────────

def get_jobs_by_status() -> list[dict]:
    c = get_conn()
    rows = c.execute("""
        SELECT job_status, COUNT(*) AS cnt,
               COALESCE(SUM(quoted_amount), 0) AS quoted_total
        FROM crm_jobs GROUP BY job_status
    """).fetchall()
    return [dict(r) for r in rows]


def get_recent_jobs(limit: int = 10) -> list[dict]:
    c = get_conn()
    rows = c.execute("""
        SELECT * FROM crm_jobs
        ORDER BY updated_at DESC, scheduled_date DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_monthly_revenue() -> list[dict]:
    _ORDER = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    c = get_conn()
    rows = c.execute("""
        SELECT scheduled_month,
               COUNT(*) AS job_count,
               COALESCE(SUM(quoted_amount), 0) AS quoted,
               COALESCE(SUM(actual_amount), 0)  AS actual
        FROM crm_jobs
        WHERE scheduled_month IS NOT NULL AND scheduled_month != ''
        GROUP BY scheduled_month
    """).fetchall()
    data = {r["scheduled_month"]: dict(r) for r in rows}
    return [data[m] for m in _ORDER if m in data]


# ── Geocoding ─────────────────────────────────────────────────────────────────

def _ensure_geo_columns() -> None:
    c = get_conn()
    for col in ("lat", "lng"):
        try:
            c.execute(f"ALTER TABLE crm_sites ADD COLUMN {col} REAL")
            c.commit()
        except Exception:
            pass


def geocode_sites() -> int:
    """Populate lat/lng for sites with a zip but no coordinates. Returns count updated."""
    _ensure_geo_columns()
    c = get_conn()
    rows = c.execute(
        "SELECT site_id, zip FROM crm_sites WHERE lat IS NULL AND zip IS NOT NULL AND zip != ''"
    ).fetchall()
    if not rows:
        return 0
    try:
        import pgeocode
        import pandas as pd
        nomi = pgeocode.Nominatim("US")
    except ImportError:
        return 0

    zip_to_sites: dict[str, list[str]] = {}
    for r in rows:
        zp = (r["zip"] or "").strip()[:5]
        if zp:
            zip_to_sites.setdefault(zp, []).append(r["site_id"])

    updated = 0
    for zp, site_ids in zip_to_sites.items():
        try:
            res = nomi.query_postal_code(zp)
            lat = float(res.latitude)
            lng = float(res.longitude)
            if pd.notna(lat) and pd.notna(lng):
                for sid in site_ids:
                    c.execute("UPDATE crm_sites SET lat=?, lng=? WHERE site_id=?",
                              (lat, lng, sid))
                    updated += 1
        except Exception:
            continue
    c.commit()
    return updated


def get_sites_with_coords() -> list[dict]:
    _ensure_geo_columns()
    c = get_conn()
    return [dict(r) for r in c.execute(
        "SELECT site_id, name, city, state, status, managed_by, budget, "
        "submittal_due_date, lat, lng FROM crm_sites WHERE lat IS NOT NULL AND lng IS NOT NULL"
    ).fetchall()]

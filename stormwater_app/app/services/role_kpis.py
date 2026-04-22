"""
app/services/role_kpis.py
KPI queries for each user role — uses the shared get_conn() so the
tables are always initialized before queries run.
"""

from __future__ import annotations
from datetime import date, timedelta
from .db import get_conn


def _ensure_tables() -> None:
    try:
        from .crm_db import init_crm_tables
        init_crm_tables()
    except Exception:
        pass


def _today() -> str:
    return date.today().isoformat()


def _week_bounds() -> tuple[str, str]:
    today = date.today()
    mon = today - timedelta(days=today.weekday())
    sun = mon + timedelta(days=6)
    return mon.isoformat(), sun.isoformat()


def _month_label() -> str:
    return date.today().strftime("%B %Y")


# ── Ops KPIs ──────────────────────────────────────────────────────────────────

def get_ops_kpis() -> dict:
    _ensure_tables()
    empty = {"jobs_scheduled_this_week": 0, "jobs_overdue": 0,
             "jobs_in_progress": 0, "revenue_scheduled_this_week": 0.0,
             "jobs_need_scheduling": 0}
    try:
        c = get_conn()
        today = _today()
        mon, sun = _week_bounds()
        return {
            "jobs_scheduled_this_week": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE scheduled_date BETWEEN ? AND ?",
                (mon, sun),
            ).fetchone()[0],
            "jobs_overdue": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE scheduled_date < ? AND job_status NOT IN ('Complete')",
                (today,),
            ).fetchone()[0],
            "jobs_in_progress": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE job_status IN ('Scheduled','Report in Progress','Ready for Review')",
            ).fetchone()[0],
            "revenue_scheduled_this_week": c.execute(
                "SELECT COALESCE(SUM(quoted_amount),0) FROM crm_jobs WHERE scheduled_date BETWEEN ? AND ?",
                (mon, sun),
            ).fetchone()[0],
            "jobs_need_scheduling": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE job_status='Need to Schedule'",
            ).fetchone()[0],
        }
    except Exception:
        return empty


def get_ops_todays_jobs() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        rows = c.execute(
            "SELECT job_id, job_site, service, job_status, owner, scheduled_date, location"
            " FROM crm_jobs WHERE scheduled_date=? ORDER BY job_site",
            (_today(),),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_ops_week_jobs() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        mon, sun = _week_bounds()
        rows = c.execute(
            "SELECT job_id, job_site, service, job_status, owner, scheduled_date, location"
            " FROM crm_jobs WHERE scheduled_date BETWEEN ? AND ? ORDER BY scheduled_date, job_site",
            (mon, sun),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_ops_overdue_jobs() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        rows = c.execute(
            "SELECT job_id, job_site, service, job_status, owner, scheduled_date"
            " FROM crm_jobs WHERE scheduled_date < ? AND job_status NOT IN ('Complete')"
            " ORDER BY scheduled_date ASC LIMIT 20",
            (_today(),),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Compliance KPIs ───────────────────────────────────────────────────────────

def get_compliance_kpis() -> dict:
    _ensure_tables()
    empty = {"submittals_due_30d": 0, "submittals_overdue": 0,
             "leads_expiring_30d": 0, "inspections_completed_mtd": 0,
             "active_sites": 0}
    try:
        c = get_conn()
        today = _today()
        in_30 = (date.today() + timedelta(days=30)).isoformat()
        month = _month_label()
        return {
            "submittals_due_30d": c.execute(
                "SELECT COUNT(*) FROM crm_sites WHERE submittal_due_date BETWEEN ? AND ?",
                (today, in_30),
            ).fetchone()[0],
            "submittals_overdue": c.execute(
                "SELECT COUNT(*) FROM crm_sites WHERE submittal_due_date < ? AND submittal_due_date != ''",
                (today,),
            ).fetchone()[0],
            "leads_expiring_30d": c.execute(
                "SELECT COUNT(*) FROM crm_leads WHERE expires BETWEEN ? AND ?",
                (today, in_30),
            ).fetchone()[0],
            "inspections_completed_mtd": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE job_status='Complete'"
                " AND (service LIKE '%Inspection%' OR service LIKE '%inspection%')"
                " AND scheduled_month=?",
                (month,),
            ).fetchone()[0],
            "active_sites": c.execute(
                "SELECT COUNT(*) FROM crm_sites WHERE status='Active'",
            ).fetchone()[0],
        }
    except Exception:
        return empty


def get_compliance_upcoming_submittals() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        today = _today()
        in_60 = (date.today() + timedelta(days=60)).isoformat()
        rows = c.execute(
            "SELECT site_id, name, city, state, submittal_due_date, status"
            " FROM crm_sites WHERE submittal_due_date BETWEEN ? AND ?"
            " ORDER BY submittal_due_date ASC LIMIT 25",
            (today, in_60),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_compliance_overdue_submittals() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        rows = c.execute(
            "SELECT site_id, name, city, state, submittal_due_date, status"
            " FROM crm_sites WHERE submittal_due_date < ? AND submittal_due_date != ''"
            " ORDER BY submittal_due_date ASC LIMIT 20",
            (_today(),),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_compliance_expiring_leads() -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        today = _today()
        in_30 = (date.today() + timedelta(days=30)).isoformat()
        rows = c.execute(
            "SELECT lead_id, name, state, total_amount, submittal_deadline, expires"
            " FROM crm_leads WHERE expires BETWEEN ? AND ?"
            " ORDER BY expires ASC LIMIT 20",
            (today, in_30),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Owner KPIs ────────────────────────────────────────────────────────────────

def get_owner_kpis() -> dict:
    _ensure_tables()
    empty = {"pipeline_value": 0.0, "revenue_mtd": 0.0, "open_jobs": 0,
             "active_sites": 0, "quoted_open": 0.0, "jobs_completed_mtd": 0}
    try:
        c = get_conn()
        month = _month_label()
        return {
            "pipeline_value": c.execute(
                "SELECT COALESCE(SUM(total_amount),0) FROM crm_leads",
            ).fetchone()[0],
            "revenue_mtd": c.execute(
                "SELECT COALESCE(SUM(actual_amount),0) FROM crm_jobs"
                " WHERE job_status='Complete' AND scheduled_month=?",
                (month,),
            ).fetchone()[0],
            "open_jobs": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE job_status NOT IN ('Complete')",
            ).fetchone()[0],
            "active_sites": c.execute(
                "SELECT COUNT(*) FROM crm_sites WHERE status='Active'",
            ).fetchone()[0],
            "quoted_open": c.execute(
                "SELECT COALESCE(SUM(quoted_amount),0) FROM crm_jobs"
                " WHERE job_status NOT IN ('Complete')",
            ).fetchone()[0],
            "jobs_completed_mtd": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE job_status='Complete' AND scheduled_month=?",
                (month,),
            ).fetchone()[0],
        }
    except Exception:
        return empty


def get_owner_recent_jobs(limit: int = 15) -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        rows = c.execute(
            "SELECT job_id, job_site, service, job_status, owner,"
            " quoted_amount, actual_amount, scheduled_date"
            " FROM crm_jobs ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Worker KPIs ───────────────────────────────────────────────────────────────

def get_worker_kpis(owner_name: str) -> dict:
    _ensure_tables()
    empty = {"my_jobs_today": 0, "my_jobs_this_week": 0, "my_completed_today": 0}
    try:
        c = get_conn()
        today = _today()
        mon, sun = _week_bounds()
        like = f"%{owner_name}%"
        return {
            "my_jobs_today": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE owner LIKE ? AND scheduled_date=?",
                (like, today),
            ).fetchone()[0],
            "my_jobs_this_week": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE owner LIKE ? AND scheduled_date BETWEEN ? AND ?",
                (like, mon, sun),
            ).fetchone()[0],
            "my_completed_today": c.execute(
                "SELECT COUNT(*) FROM crm_jobs WHERE owner LIKE ? AND job_status='Complete' AND scheduled_date=?",
                (like, today),
            ).fetchone()[0],
        }
    except Exception:
        return empty


def get_worker_jobs(owner_name: str) -> list[dict]:
    _ensure_tables()
    try:
        c = get_conn()
        mon, sun = _week_bounds()
        like = f"%{owner_name}%"
        rows = c.execute(
            "SELECT job_id, job_site, service, job_status, scheduled_date, location, notes"
            " FROM crm_jobs WHERE owner LIKE ? AND scheduled_date BETWEEN ? AND ?"
            " ORDER BY scheduled_date, job_site",
            (like, mon, sun),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

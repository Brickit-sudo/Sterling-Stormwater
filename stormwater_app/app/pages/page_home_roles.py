"""
app/pages/page_home_roles.py
Role-based home dashboards — one render function per role.
Dispatched by render() based on st.session_state.user_role.
"""

from __future__ import annotations
import streamlit as st
from app.session import set_page

# ── Shared helpers ────────────────────────────────────────────────────────────

_STATUS_COLOR = {
    "Need to Schedule":   "#e2445c",
    "Scheduled":          "#ffcb00",
    "Report in Progress": "#579bfc",
    "Ready for Review":   "#a25ddc",
    "Complete":           "#00c875",
}


def _kpi(label: str, value, delta: str = "", color: str = "#1AB738") -> None:
    delta_html = (
        f'<div style="font-size:11px;color:#9699a6;margin-top:2px">{delta}</div>'
        if delta else ""
    )
    if isinstance(value, float):
        val_str = f"${value:,.0f}"
    else:
        val_str = str(value)
    st.markdown(
        f'<div style="background:#1c2240;border:1px solid rgba(255,255,255,0.08);'
        f'border-radius:10px;padding:16px 18px;min-height:80px">'
        f'<div style="font-size:11px;color:#9699a6;text-transform:uppercase;'
        f'letter-spacing:.08em;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:28px;font-weight:700;color:{color};line-height:1">{val_str}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


def _status_badge(status: str) -> str:
    color = _STATUS_COLOR.get(status, "#9699a6")
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'font-size:11px;background:{color}22;color:{color};border:1px solid {color}44">'
        f'{status}</span>'
    )


def _section(title: str) -> None:
    st.markdown(
        f'<div style="font-size:11px;font-weight:600;color:#9699a6;text-transform:uppercase;'
        f'letter-spacing:.08em;margin:24px 0 10px">{title}</div>',
        unsafe_allow_html=True,
    )


def _quick_btn(icon: str, label: str, page: str, col) -> None:
    with col:
        if st.button(f"{icon}  {label}", use_container_width=True, key=f"qb_{page}_{label}"):
            set_page(page)
            st.rerun()


# ── Role: Operations Manager ──────────────────────────────────────────────────

def _render_ops() -> None:
    from app.services.role_kpis import get_ops_kpis, get_ops_todays_jobs, get_ops_overdue_jobs, get_ops_week_jobs

    user = st.session_state.get("current_user", {})
    name = user.get("name", "Operations")

    st.markdown(
        f'<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 2px">👷 {name}</h2>'
        f'<p style="color:#9699a6;font-size:13px;margin:0 0 20px">Operations Dashboard</p>',
        unsafe_allow_html=True,
    )

    kpis = get_ops_kpis()

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("This Week", kpis["jobs_scheduled_this_week"], "jobs scheduled", "#579bfc")
    with c2: _kpi("Overdue", kpis["jobs_overdue"], "need attention", "#e2445c")
    with c3: _kpi("In Progress", kpis["jobs_in_progress"], "active jobs")
    with c4: _kpi("Need Scheduling", kpis["jobs_need_scheduling"], "unscheduled", "#ffcb00")

    # Quick actions
    _section("Quick Actions")
    q1, q2, q3, q4 = st.columns(4)
    _quick_btn("🔧", "All Jobs", "crm_jobs", q1)
    _quick_btn("📅", "Calendar", "calendar", q2)
    _quick_btn("📷", "Photosheet", "photosheet", q3)
    _quick_btn("⚙️", "New Report", "setup", q4)

    # Today's jobs
    today_jobs = get_ops_todays_jobs()
    week_jobs = get_ops_week_jobs()
    overdue = get_ops_overdue_jobs()

    tab1, tab2, tab3 = st.tabs([
        f"Today ({len(today_jobs)})",
        f"This Week ({len(week_jobs)})",
        f"🔴 Overdue ({len(overdue)})",
    ])

    with tab1:
        if not today_jobs:
            st.caption("No jobs scheduled for today.")
        else:
            _render_job_table(today_jobs)

    with tab2:
        if not week_jobs:
            st.caption("No jobs scheduled this week.")
        else:
            _render_job_table(week_jobs)

    with tab3:
        if not overdue:
            st.success("No overdue jobs — great work!")
        else:
            _render_job_table(overdue, show_date=True)


def _render_job_table(jobs: list[dict], show_date: bool = False) -> None:
    rows_html = ""
    for j in jobs:
        badge = _status_badge(j.get("job_status", ""))
        date_cell = (
            f'<td style="color:#9699a6;font-size:12px">{j.get("scheduled_date","")}</td>'
            if show_date else ""
        )
        rows_html += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05)">'
            f'<td style="padding:8px 6px;font-size:13px">{j.get("job_site","")}</td>'
            f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{j.get("service","")}</td>'
            f'<td style="padding:8px 6px">{badge}</td>'
            f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{j.get("owner","")}</td>'
            f'{date_cell}'
            f'</tr>'
        )
    date_header = '<th style="color:#9699a6;font-size:11px;padding:6px">Date</th>' if show_date else ""
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1)">'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Site</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Service</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Status</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Owner</th>'
        f'{date_header}'
        f'</tr></thead><tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )


# ── Role: Compliance Manager ──────────────────────────────────────────────────

def _render_compliance() -> None:
    from app.services.role_kpis import (
        get_compliance_kpis, get_compliance_upcoming_submittals,
        get_compliance_overdue_submittals, get_compliance_expiring_leads,
    )

    user = st.session_state.get("current_user", {})
    name = user.get("name", "Compliance")

    st.markdown(
        f'<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 2px">📋 {name}</h2>'
        f'<p style="color:#9699a6;font-size:13px;margin:0 0 20px">Compliance Dashboard</p>',
        unsafe_allow_html=True,
    )

    kpis = get_compliance_kpis()

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Submittals Due 30d", kpis["submittals_due_30d"], "upcoming", "#ffcb00")
    with c2: _kpi("Overdue Submittals", kpis["submittals_overdue"], "past due", "#e2445c")
    with c3: _kpi("Leads Expiring 30d", kpis["leads_expiring_30d"], "at risk", "#a25ddc")
    with c4: _kpi("Inspections MTD", kpis["inspections_completed_mtd"], "completed this month")

    _section("Quick Actions")
    q1, q2, q3, q4 = st.columns(4)
    _quick_btn("🗄️", "Sites", "crm_sites", q1)
    _quick_btn("🎯", "Leads", "crm_leads", q2)
    _quick_btn("📊", "New Report", "setup", q3)
    _quick_btn("📁", "Archive", "crm_files", q4)

    upcoming = get_compliance_upcoming_submittals()
    overdue = get_compliance_overdue_submittals()
    expiring = get_compliance_expiring_leads()

    tab1, tab2, tab3 = st.tabs([
        f"Upcoming Submittals ({len(upcoming)})",
        f"🔴 Overdue ({len(overdue)})",
        f"⚠️ Leads Expiring ({len(expiring)})",
    ])

    with tab1:
        if not upcoming:
            st.caption("No submittals due in the next 60 days.")
        else:
            _render_submittal_table(upcoming)

    with tab2:
        if not overdue:
            st.success("No overdue submittals.")
        else:
            _render_submittal_table(overdue, overdue=True)

    with tab3:
        if not expiring:
            st.caption("No leads expiring in the next 30 days.")
        else:
            _render_lead_expiry_table(expiring)


def _render_submittal_table(rows: list[dict], overdue: bool = False) -> None:
    html_rows = ""
    for r in rows:
        due = r.get("submittal_due_date", "")
        color = "#e2445c" if overdue else "#ffcb00"
        html_rows += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05)">'
            f'<td style="padding:8px 6px;font-size:13px">{r.get("name","")}</td>'
            f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{r.get("city","")}, {r.get("state","")}</td>'
            f'<td style="padding:8px 6px;font-size:12px;color:{color}">{due}</td>'
            f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{r.get("status","")}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1)">'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Site</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Location</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Due Date</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Status</th>'
        f'</tr></thead><tbody>{html_rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_lead_expiry_table(rows: list[dict]) -> None:
    html_rows = ""
    for r in rows:
        amt = r.get("total_amount") or 0
        html_rows += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05)">'
            f'<td style="padding:8px 6px;font-size:13px">{r.get("name","")}</td>'
            f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{r.get("state","")}</td>'
            f'<td style="padding:8px 6px;color:#1AB738;font-size:12px">${amt:,.0f}</td>'
            f'<td style="padding:8px 6px;color:#a25ddc;font-size:12px">{r.get("expires","")}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1)">'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Lead</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">State</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Value</th>'
        f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Expires</th>'
        f'</tr></thead><tbody>{html_rows}</tbody></table>',
        unsafe_allow_html=True,
    )


# ── Role: Owner ───────────────────────────────────────────────────────────────

def _render_owner() -> None:
    from app.services.role_kpis import get_owner_kpis, get_owner_recent_jobs

    user = st.session_state.get("current_user", {})
    name = user.get("name", "Owner")

    st.markdown(
        f'<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 2px">📈 {name}</h2>'
        f'<p style="color:#9699a6;font-size:13px;margin:0 0 20px">Executive Overview</p>',
        unsafe_allow_html=True,
    )

    kpis = get_owner_kpis()

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Pipeline Value", float(kpis["pipeline_value"]), "total leads", "#a25ddc")
    with c2: _kpi("Revenue MTD", float(kpis["revenue_mtd"]), "completed this month")
    with c3: _kpi("Open Jobs", kpis["open_jobs"], "in progress", "#ffcb00")
    with c4: _kpi("Quoted Open", float(kpis["quoted_open"]), "outstanding quoted", "#579bfc")

    _section("Quick Actions")
    q1, q2, q3, q4 = st.columns(4)
    _quick_btn("🧾", "Invoices", "crm_invoices", q1)
    _quick_btn("💰", "Quotes", "crm_quotes", q2)
    _quick_btn("🎯", "Leads", "crm_leads", q3)
    _quick_btn("📈", "Insights", "trends", q4)

    _section("Recent Jobs")
    recent = get_owner_recent_jobs(20)
    if not recent:
        st.caption("No jobs found.")
    else:
        html_rows = ""
        for j in recent:
            quoted = j.get("quoted_amount") or 0
            actual = j.get("actual_amount") or 0
            diff = actual - quoted
            diff_color = "#1AB738" if diff >= 0 else "#e2445c"
            diff_str = f'+${diff:,.0f}' if diff >= 0 else f'-${abs(diff):,.0f}'
            badge = _status_badge(j.get("job_status", ""))
            html_rows += (
                f'<tr style="border-bottom:1px solid rgba(255,255,255,0.05)">'
                f'<td style="padding:8px 6px;font-size:13px">{j.get("job_site","")}</td>'
                f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">{j.get("service","")}</td>'
                f'<td style="padding:8px 6px">{badge}</td>'
                f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">${quoted:,.0f}</td>'
                f'<td style="padding:8px 6px;color:#9699a6;font-size:12px">${actual:,.0f}</td>'
                f'<td style="padding:8px 6px;color:{diff_color};font-size:12px">{diff_str if actual else "—"}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1)">'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Site</th>'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Service</th>'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Status</th>'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Quoted</th>'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Actual</th>'
            f'<th style="color:#9699a6;font-size:11px;padding:6px;text-align:left">Var</th>'
            f'</tr></thead><tbody>{html_rows}</tbody></table>',
            unsafe_allow_html=True,
        )


# ── Role: Worker / Field Tech ─────────────────────────────────────────────────

def _render_worker() -> None:
    from app.services.role_kpis import get_worker_kpis, get_worker_jobs

    user = st.session_state.get("current_user", {})
    name = user.get("name", "Field Tech")

    st.markdown(
        f'<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 2px">🔧 {name}</h2>'
        f'<p style="color:#9699a6;font-size:13px;margin:0 0 20px">My Work</p>',
        unsafe_allow_html=True,
    )

    kpis = get_worker_kpis(name)

    # Large touch-friendly KPI cards
    c1, c2, c3 = st.columns(3)
    with c1:
        _kpi("Today", kpis["my_jobs_today"], "jobs assigned", "#1AB738")
    with c2:
        _kpi("This Week", kpis["my_jobs_this_week"], "total jobs", "#579bfc")
    with c3:
        _kpi("Done Today", kpis["my_completed_today"], "completed", "#00c875")

    # Primary CTAs — big touch targets
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("📷  Upload Photos (Photosheet)", use_container_width=True, type="primary",
                     key="worker_photosheet"):
            set_page("photosheet")
            st.rerun()
    with btn2:
        if st.button("✏️  Write Report", use_container_width=True, key="worker_report"):
            set_page("setup")
            st.rerun()

    _section("My Jobs This Week")
    jobs = get_worker_jobs(name)
    if not jobs:
        st.info("No jobs assigned to you this week.", icon="✅")
    else:
        for j in jobs:
            status = j.get("job_status", "")
            color = _STATUS_COLOR.get(status, "#9699a6")
            is_done = status == "Complete"
            st.markdown(
                f'<div style="background:#1c2240;border:1px solid rgba(255,255,255,0.08);'
                f'border-left:4px solid {color};border-radius:8px;padding:14px 16px;'
                f'margin-bottom:8px;{"opacity:0.55;" if is_done else ""}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<div style="font-size:14px;font-weight:600;color:#d5d8df">{j.get("job_site","")}</div>'
                f'<div style="font-size:12px;color:#9699a6;margin-top:2px">'
                f'{j.get("service","")}  ·  {j.get("scheduled_date","")}</div>'
                f'{("<div style=\"font-size:11px;color:#9699a6;margin-top:4px\">" + j.get("location","") + "</div>") if j.get("location") else ""}'
                f'</div>'
                f'<span style="display:inline-block;padding:4px 10px;border-radius:6px;'
                f'font-size:11px;background:{color}22;color:{color};border:1px solid {color}44">'
                f'{status}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


# ── Main dispatcher ───────────────────────────────────────────────────────────

_ROLE_LABELS = {
    "ops":        "Operations Manager",
    "compliance": "Compliance Manager",
    "owner":      "Owner",
    "worker":     "Worker / Field Tech",
}

_RENDERERS = {
    "ops":        _render_ops,
    "compliance": _render_compliance,
    "owner":      _render_owner,
    "worker":     _render_worker,
}


def render() -> None:
    role = st.session_state.get("user_role", "ops")
    renderer = _RENDERERS.get(role, _render_ops)
    renderer()

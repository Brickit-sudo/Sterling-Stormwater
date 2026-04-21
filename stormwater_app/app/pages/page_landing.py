"""
app/pages/page_landing.py
Sterling Stormwater — analytics dashboard home screen.
"""

import base64
import datetime
from pathlib import Path

import streamlit as st

_LOGO_PATH = Path("assets/sterling_logo.png")

_STATUS_COLOR = {
    "Need to Schedule":   "#e2445c",
    "Scheduled":          "#ffcb00",
    "Report in Progress": "#579bfc",
    "Ready for Review":   "#a25ddc",
    "Complete":           "#1AB738",
}
_STATUS_ORDER = [
    "Need to Schedule", "Scheduled", "Report in Progress",
    "Ready for Review", "Complete",
]


def _logo_b64() -> str:
    if _LOGO_PATH.exists():
        return base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    return ""


def _kpi(label: str, value, sub: str = "", color: str = "#1AB738") -> None:
    sub_html = (f'<div style="font-size:11px;color:#6e6f8f;margin-top:4px">{sub}</div>'
                if sub else "")
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1c2240 0%,#1a1e38 100%);"'
        f'border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:18px 20px;'
        f'box-shadow:0 4px 16px rgba(0,0,0,0.25)">'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:0.12em;color:#6e6f8f;'
        f'margin-bottom:6px">{label}</div>'
        f'<div style="font-size:1.75rem;font-weight:800;color:{color};'
        f'letter-spacing:-0.02em;line-height:1">{value}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _pipeline_bar(status: str, count: int, total: int, quoted: float) -> None:
    color   = _STATUS_COLOR.get(status, "#9699a6")
    pct     = int(count / total * 100) if total else 0
    q_str   = f"${quoted:,.0f}" if quoted else ""
    q_html  = (f'<div style="width:72px;text-align:right;font-size:11px;color:#6e6f8f">{q_str}</div>'
               if q_str else '<div style="width:72px"></div>')
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;'
        f'border-bottom:1px solid rgba(255,255,255,0.04)">'
        f'<div style="width:140px;font-size:12px;color:#9699a6;flex-shrink:0">{status}</div>'
        f'<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:4px;height:8px;overflow:hidden">'
        f'<div style="width:{pct}%;height:8px;background:{color};border-radius:4px;'
        f'transition:width 400ms ease"></div></div>'
        f'<div style="width:32px;text-align:right;font-size:13px;font-weight:700;color:{color}">{count}</div>'
        f'{q_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render():
    # ── Header ────────────────────────────────────────────────────────────────
    logo_b64 = _logo_b64()
    logo_tag = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="height:32px;display:inline-block;vertical-align:middle;'
        f'filter:drop-shadow(0 0 12px rgba(26,183,56,0.30));margin-right:12px" />'
        if logo_b64 else ""
    )
    today = datetime.date.today().strftime("%B %d, %Y")

    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:18px 0 14px 0;border-bottom:1px solid rgba(255,255,255,0.06)">'
        f'<div style="display:flex;align-items:center">'
        f'{logo_tag}'
        f'<div>'
        f'<div style="font-size:16px;font-weight:700;color:#d5d8df">Sterling Stormwater</div>'
        f'<div style="font-size:11px;color:#6e6f8f;font-family:\'JetBrains Mono\',monospace">'
        f'Field Service Dashboard</div>'
        f'</div></div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#6e6f8f">'
        f'{today}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Fetch analytics data ──────────────────────────────────────────────────
    stats = {}
    jobs_by_status = []
    recent_jobs    = []
    monthly_rev    = []
    try:
        from app.services.crm_db import (
            get_crm_stats, get_jobs_by_status, get_recent_jobs,
            get_monthly_revenue, init_crm_tables,
        )
        init_crm_tables()
        stats          = get_crm_stats()
        jobs_by_status = get_jobs_by_status()
        recent_jobs    = get_recent_jobs(limit=8)
        monthly_rev    = get_monthly_revenue()
    except Exception:
        pass

    # ── Quick actions ──────────────────────────────────────────────────────────
    qa1, qa2, qa3, qa4 = st.columns(4, gap="small")
    with qa1:
        if st.button("📷  Photosheet", use_container_width=True, type="primary"):
            st.session_state.current_page = "photosheet"
            st.session_state.ps_step      = "upload"
            st.rerun()
    with qa2:
        if st.button("📄  Full Report", use_container_width=True):
            st.session_state.current_page = "setup"
            st.rerun()
    with qa3:
        if st.button("🔧  New Job", use_container_width=True):
            st.session_state["crm_job_add"] = True
            st.session_state.current_page   = "crm_jobs"
            st.rerun()
    with qa4:
        if st.button("💬  Log Comm", use_container_width=True):
            st.session_state["crm_comm_add"] = True
            st.session_state.current_page    = "crm_comms"
            st.rerun()

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="small")
    open_jobs    = stats.get("open_jobs", 0)
    total_sites  = stats.get("sites", 0)
    total_leads  = stats.get("leads", 0)
    quoted_total = stats.get("quoted_total", 0)

    with k1:
        _kpi("Open Jobs", open_jobs,
             f"{stats.get('jobs', 0)} total", "#e2445c" if open_jobs > 10 else "#1AB738")
    with k2:
        _kpi("Active Sites", total_sites, "managed properties")
    with k3:
        _kpi("Pipeline", f"${quoted_total:,.0f}" if quoted_total else "$0",
             "quoted (open jobs)", "#ffcb00")
    with k4:
        _kpi("Open Leads", total_leads, f"{stats.get('contacts', 0)} contacts", "#579bfc")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # ── Two-column layout: Pipeline + Revenue ─────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="medium")

    with col_left:
        st.markdown(
            '<div style="font-size:13px;font-weight:600;color:#9699a6;'
            'text-transform:uppercase;letter-spacing:0.08em;'
            'margin-bottom:10px">Job Pipeline</div>',
            unsafe_allow_html=True,
        )
        if jobs_by_status:
            total_jobs = sum(r.get("cnt", 0) for r in jobs_by_status)
            status_map = {r["job_status"]: r for r in jobs_by_status}
            for s in _STATUS_ORDER:
                if s in status_map:
                    row = status_map[s]
                    _pipeline_bar(s, row["cnt"], total_jobs, row.get("quoted_total", 0))
            # Any statuses not in standard order
            for row in jobs_by_status:
                if row["job_status"] not in _STATUS_ORDER:
                    _pipeline_bar(row["job_status"], row["cnt"], total_jobs,
                                  row.get("quoted_total", 0))
        else:
            st.caption("No job data yet.")

    with col_right:
        st.markdown(
            '<div style="font-size:13px;font-weight:600;color:#9699a6;'
            'text-transform:uppercase;letter-spacing:0.08em;'
            'margin-bottom:10px">Monthly Revenue</div>',
            unsafe_allow_html=True,
        )
        if monthly_rev:
            max_quoted = max((r.get("quoted", 0) for r in monthly_rev), default=1) or 1
            for row in monthly_rev[-6:]:
                month   = row["scheduled_month"][:3]
                quoted  = row.get("quoted", 0)
                cnt     = row.get("job_count", 0)
                bar_pct = int(quoted / max_quoted * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04)">'
                    f'<div style="width:32px;font-size:11px;color:#9699a6;'
                    f'font-family:\'JetBrains Mono\',monospace">{month}</div>'
                    f'<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:4px;'
                    f'height:6px;overflow:hidden">'
                    f'<div style="width:{bar_pct}%;height:6px;background:#1AB738;'
                    f'border-radius:4px"></div></div>'
                    f'<div style="width:64px;text-align:right;font-size:11px;'
                    f'color:#d5d8df">${quoted:,.0f}</div>'
                    f'<div style="width:28px;text-align:right;font-size:10px;'
                    f'color:#6e6f8f">{cnt}j</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No monthly data yet.")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # ── Recent Jobs ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:600;color:#9699a6;'
        'text-transform:uppercase;letter-spacing:0.08em;'
        'margin-bottom:10px">Recent Jobs</div>',
        unsafe_allow_html=True,
    )

    if recent_jobs:
        hdr1, hdr2, hdr3, hdr4, hdr5 = st.columns([3, 2, 2, 1, 1])
        for h, col in zip(["Site", "Service", "Status", "Owner", "Quoted"],
                          [hdr1, hdr2, hdr3, hdr4, hdr5]):
            col.markdown(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
                f'text-transform:uppercase;letter-spacing:0.10em;color:#4b4e69;'
                f'padding-bottom:4px">{h}</div>',
                unsafe_allow_html=True,
            )

        for job in recent_jobs:
            jstatus = job.get("job_status", "")
            jcolor  = _STATUS_COLOR.get(jstatus, "#9699a6")
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
            with c1:
                site = job.get("job_site") or "—"
                st.markdown(
                    f'<div style="font-size:13px;color:#d5d8df;padding:6px 0">'
                    f'{site[:32]}{"…" if len(site) > 32 else ""}</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                svc = job.get("service") or "—"
                st.markdown(
                    f'<div style="font-size:12px;color:#9699a6;padding:6px 0">{svc[:24]}</div>',
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f'<div style="padding:6px 0">'
                    f'<span style="background:{jcolor}20;color:{jcolor};padding:2px 7px;'
                    f'border-radius:8px;font-size:11px;font-weight:600">{jstatus or "—"}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c4:
                owner = (job.get("owner") or "").split()[0] if job.get("owner") else "—"
                st.markdown(
                    f'<div style="font-size:11px;color:#9699a6;padding:6px 0">{owner}</div>',
                    unsafe_allow_html=True,
                )
            with c5:
                q = job.get("quoted_amount")
                st.markdown(
                    f'<div style="font-size:12px;color:#1AB738;padding:6px 0;'
                    f'font-weight:600">{"$"+f"{q:,.0f}" if q else "—"}</div>',
                    unsafe_allow_html=True,
                )

        if st.button("View All Jobs →", key="dash_view_jobs"):
            st.session_state.current_page = "crm_jobs"
            st.rerun()
    else:
        st.caption("No jobs yet. Add your first job from the Jobs page.")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:32px 0 8px 0;">'
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        'color:#3D4D5C;letter-spacing:0.08em">'
        'Sterling Stormwater Maintenance Services, Inc'
        ' &nbsp;·&nbsp; Report Generator v1.0'
        '</div></div>',
        unsafe_allow_html=True,
    )

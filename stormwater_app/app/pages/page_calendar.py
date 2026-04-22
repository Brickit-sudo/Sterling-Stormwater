"""
app/pages/page_calendar.py
Sterling Stormwater — Calendar view.
Shows jobs, submittal deadlines, and lead expiry dates on a FullCalendar.
"""

import streamlit as st
from streamlit_calendar import calendar as st_calendar
from app.services.crm_db import get_all_jobs, get_all_crm_sites, get_all_leads

_STATUS_COLOR = {
    "Need to Schedule": "#e2445c",
    "Scheduled":        "#ffcb00",
    "Report in Progress": "#579bfc",
    "Ready for Review": "#a25ddc",
    "Complete":         "#00c875",
}

_CAL_OPTIONS = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left":   "prev,next today",
        "center": "title",
        "right":  "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
    },
    "height":     "auto",
    "editable":   False,
    "selectable": True,
    "dayMaxEvents": 4,
    "navLinks":   True,
    "businessHours": True,
    "nowIndicator": True,
}

_CAL_CSS = """
.fc { font-family: 'Figtree', -apple-system, sans-serif !important; }
.fc-toolbar-title { font-size: 1.1rem !important; font-weight: 600 !important; }
.fc-button-primary {
    background: #2b2d42 !important;
    border-color: rgba(255,255,255,0.1) !important;
    font-size: 12px !important;
}
.fc-button-primary:not(:disabled).fc-button-active,
.fc-button-primary:not(:disabled):active {
    background: #1ab738 !important;
    border-color: #1ab738 !important;
}
.fc-day-today { background: rgba(26,183,56,0.06) !important; }
.fc-event { cursor: pointer; font-size: 11px !important; }
.fc-daygrid-more-link { font-size: 11px !important; color: #9699a6 !important; }
"""


def _build_events(show_jobs: bool, show_submittals: bool, show_leads: bool) -> list[dict]:
    events: list[dict] = []

    if show_jobs:
        for job in get_all_jobs():
            date = (job.get("scheduled_date") or "").strip()
            if not date:
                continue
            color = _STATUS_COLOR.get(job.get("job_status", ""), "#579bfc")
            events.append({
                "id":    job.get("job_id", ""),
                "title": f"🔧 {job.get('job_site', '')} — {job.get('service', '')}",
                "start": date,
                "allDay": True,
                "backgroundColor": color,
                "borderColor":     color,
                "textColor":       "#fff" if color != "#ffcb00" else "#1a1b2e",
                "extendedProps": {
                    "type":   "job",
                    "status": job.get("job_status", ""),
                    "owner":  job.get("owner", ""),
                    "quoted": job.get("quoted_amount", ""),
                    "actual": job.get("actual_amount", ""),
                    "site":   job.get("job_site", ""),
                    "service": job.get("service", ""),
                },
            })

    if show_submittals:
        for site in get_all_crm_sites():
            date = (site.get("submittal_due_date") or "").strip()
            if not date:
                continue
            events.append({
                "id":    f"sub_{site.get('site_id', '')}",
                "title": f"📄 Submittal: {site.get('name', '')}",
                "start": date,
                "allDay": True,
                "backgroundColor": "#fd7e14",
                "borderColor":     "#fd7e14",
                "textColor":       "#fff",
                "extendedProps": {
                    "type":  "submittal",
                    "site":  site.get("name", ""),
                    "state": site.get("state", ""),
                },
            })

    if show_leads:
        for lead in get_all_leads():
            for field, label, color in [
                ("submittal_deadline", "📋 Deadline", "#a25ddc"),
                ("expires",           "⏰ Expires",   "#9699a6"),
            ]:
                date = (lead.get(field) or "").strip()
                if not date:
                    continue
                events.append({
                    "id":    f"{field}_{lead.get('lead_id', '')}",
                    "title": f"{label}: {lead.get('name', '')}",
                    "start": date,
                    "allDay": True,
                    "backgroundColor": color,
                    "borderColor":     color,
                    "textColor":       "#fff",
                    "extendedProps": {
                        "type":     "lead",
                        "name":     lead.get("name", ""),
                        "activity": lead.get("next_activity", ""),
                        "amount":   lead.get("total_amount", ""),
                    },
                })

    return events


def _detail_panel(ev: dict) -> None:
    props = ev.get("extendedProps", {})
    kind  = props.get("type", "")
    st.markdown(
        '<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
        'border-radius:8px;padding:14px 16px;margin-top:12px">',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {ev.get('title', '')}")
    st.caption(f"**Date:** {ev.get('start', '')}")

    if kind == "job":
        cols = st.columns(2)
        cols[0].metric("Status", props.get("status", "—"))
        cols[1].metric("Owner",  props.get("owner",  "—"))
        q = props.get("quoted")
        a = props.get("actual")
        if q or a:
            c2 = st.columns(2)
            if q:
                c2[0].metric("Quoted",  f"${float(q):,.0f}" if q else "—")
            if a:
                c2[1].metric("Actual",  f"${float(a):,.0f}" if a else "—")
        if st.button("Open Jobs →", key="cal_open_jobs"):
            from app.session import set_page
            set_page("crm_jobs")
            st.rerun()

    elif kind == "submittal":
        st.caption(f"**Site:** {props.get('site', '—')}  |  **State:** {props.get('state', '—')}")
        if st.button("Open Sites →", key="cal_open_sites"):
            from app.session import set_page
            set_page("crm_sites")
            st.rerun()

    elif kind == "lead":
        cols = st.columns(2)
        cols[0].metric("Activity", props.get("activity", "—"))
        amt = props.get("amount")
        if amt:
            cols[1].metric("Amount", f"${float(amt):,.0f}")
        if st.button("Open Leads →", key="cal_open_leads"):
            from app.session import set_page
            set_page("crm_leads")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render() -> None:
    st.markdown(
        '<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 4px">📅 Calendar</h2>'
        '<p style="color:#9699a6;font-size:13px;margin:0 0 16px">Scheduled jobs, submittals, and lead deadlines</p>',
        unsafe_allow_html=True,
    )

    # ── Filters ──────────────────────────────────────────────────────────────
    fc, *_ = st.columns([6, 2])
    with fc:
        cf1, cf2, cf3 = st.columns(3)
        show_jobs       = cf1.checkbox("🔧 Jobs",        value=True,  key="cal_jobs")
        show_submittals = cf2.checkbox("📄 Submittals",  value=True,  key="cal_subs")
        show_leads      = cf3.checkbox("🎯 Lead dates",  value=True,  key="cal_leads")

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 14px;font-size:11px;color:#9699a6">'
        + "".join(
            f'<span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;'
            f'background:{c};margin-right:4px;vertical-align:middle"></span>{lbl}</span>'
            for lbl, c in [
                ("Need to Schedule", "#e2445c"),
                ("Scheduled",        "#ffcb00"),
                ("In Progress",      "#579bfc"),
                ("Ready for Review", "#a25ddc"),
                ("Complete",         "#00c875"),
                ("Submittal",        "#fd7e14"),
                ("Lead deadline",    "#a25ddc"),
                ("Lead expiry",      "#9699a6"),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Calendar ──────────────────────────────────────────────────────────────
    events = _build_events(show_jobs, show_submittals, show_leads)
    result = st_calendar(
        events=events,
        options=_CAL_OPTIONS,
        custom_css=_CAL_CSS,
        key=f"cal_{show_jobs}_{show_submittals}_{show_leads}",
    )

    # ── Detail panel on click ─────────────────────────────────────────────────
    if result and result.get("action") == "eventClick":
        _detail_panel(result.get("event", {}))
    elif result and result.get("action") == "dateClick":
        clicked = result.get("dateStr", "")
        day_events = [e for e in events if e.get("start", "")[:10] == clicked[:10]]
        if day_events:
            st.markdown(
                f'<div style="color:#9699a6;font-size:12px;margin-top:10px">'
                f'{len(day_events)} event(s) on {clicked[:10]}</div>',
                unsafe_allow_html=True,
            )

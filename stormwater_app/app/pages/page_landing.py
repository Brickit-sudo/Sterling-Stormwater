"""
app/pages/page_landing.py
Sterling Stormwater — WorldMonitor-style map dashboard home screen.
"""

import datetime
from pathlib import Path

import pydeck as pdk
import streamlit as st

_LOGO_PATH = Path("assets/sterling_logo.png")

_STATUS_COLOR = {
    "Need to Schedule":   "#e2445c",
    "Scheduled":          "#ffcb00",
    "Report in Progress": "#579bfc",
    "Ready for Review":   "#a25ddc",
    "Complete":           "#00c875",
}
_STATUS_ORDER = [
    "Need to Schedule", "Scheduled", "Report in Progress",
    "Ready for Review", "Complete",
]

_SITE_STATUS_RGBA = {
    "Active":   [26,  183, 56,  210],
    "Inactive": [150, 153, 166, 140],
    "On Hold":  [255, 203, 0,   190],
}
_DEFAULT_SITE_RGBA = [87, 155, 252, 180]

_JOB_STATUS_RGBA = {
    "Need to Schedule":   [226, 68,  92,  200],
    "Scheduled":          [255, 203, 0,   200],
    "Report in Progress": [87,  155, 252, 200],
    "Ready for Review":   [162, 93,  220, 200],
    "Complete":           [0,   200, 117, 200],
}


# ── Map helpers ───────────────────────────────────────────────────────────────

def _site_layers(sites: list[dict], show_active: bool,
                 show_inactive: bool, show_hold: bool) -> list:
    filtered = []
    for s in sites:
        st_val = s.get("status", "Active") or "Active"
        if st_val == "Active"   and not show_active:   continue
        if st_val == "Inactive" and not show_inactive: continue
        if st_val == "On Hold"  and not show_hold:     continue
        filtered.append({
            **s,
            "color": _SITE_STATUS_RGBA.get(st_val, _DEFAULT_SITE_RGBA),
        })
    if not filtered:
        return []
    # Outer glow ring
    outer = pdk.Layer(
        "ScatterplotLayer",
        data=filtered,
        get_position=["lng", "lat"],
        get_fill_color="color",
        get_radius=800,
        radius_min_pixels=6,
        radius_max_pixels=18,
        opacity=0.25,
        pickable=False,
        stroked=False,
    )
    # Inner dot
    inner = pdk.Layer(
        "ScatterplotLayer",
        data=filtered,
        get_position=["lng", "lat"],
        get_fill_color="color",
        get_radius=400,
        radius_min_pixels=3,
        radius_max_pixels=10,
        opacity=0.9,
        pickable=True,
        stroked=True,
        line_width_min_pixels=1,
        get_line_color=[255, 255, 255, 60],
    )
    return [outer, inner]


def _job_layer(sites_by_id: dict, jobs: list[dict]) -> list:
    pts = []
    for j in jobs:
        sid  = j.get("site_id")
        site = sites_by_id.get(sid)
        if not site or not site.get("lat"):
            continue
        # Jitter slightly so jobs don't stack perfectly on sites
        import random
        rng = random.Random(j.get("job_id", ""))
        pts.append({
            "lng":    site["lng"] + rng.uniform(-0.005, 0.005),
            "lat":    site["lat"] + rng.uniform(-0.005, 0.005),
            "title":  j.get("job_site", ""),
            "service": j.get("service", ""),
            "status": j.get("job_status", ""),
            "color":  _JOB_STATUS_RGBA.get(j.get("job_status", ""),
                                           [87, 155, 252, 180]),
        })
    if not pts:
        return []
    return [pdk.Layer(
        "ScatterplotLayer",
        data=pts,
        get_position=["lng", "lat"],
        get_fill_color="color",
        get_radius=300,
        radius_min_pixels=4,
        radius_max_pixels=12,
        opacity=0.85,
        pickable=True,
        stroked=True,
        line_width_min_pixels=1,
        get_line_color=[255, 255, 255, 80],
    )]


def _submittal_layer(sites: list[dict]) -> list:
    today = datetime.date.today().isoformat()
    pts = [
        {**s, "color": [253, 126, 20, 220]}
        for s in sites
        if s.get("submittal_due_date") and s["submittal_due_date"] >= today
    ]
    if not pts:
        return []
    return [pdk.Layer(
        "ScatterplotLayer",
        data=pts,
        get_position=["lng", "lat"],
        get_fill_color=[253, 126, 20, 60],
        get_radius=1400,
        radius_min_pixels=8,
        radius_max_pixels=24,
        opacity=0.5,
        pickable=False,
        stroked=False,
    ), pdk.Layer(
        "ScatterplotLayer",
        data=pts,
        get_position=["lng", "lat"],
        get_fill_color=[253, 126, 20, 230],
        get_radius=500,
        radius_min_pixels=4,
        radius_max_pixels=12,
        opacity=1.0,
        pickable=True,
    )]


# ── KPI / chart helpers ───────────────────────────────────────────────────────

def _kpi(label: str, value, sub: str = "", color: str = "#1AB738") -> None:
    sub_html = (f'<div style="font-size:11px;color:#6e6f8f;margin-top:4px">{sub}</div>'
                if sub else "")
    st.markdown(
        f'<div style="background:#1c2240;border:1px solid rgba(255,255,255,0.08);'
        f'border-radius:10px;padding:16px 18px;box-shadow:0 4px 16px rgba(0,0,0,0.25)">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.12em;'
        f'color:#6e6f8f;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:1.65rem;font-weight:800;color:{color};'
        f'letter-spacing:-0.02em;line-height:1">{value}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _pipeline_bar(status: str, count: int, total: int, quoted: float) -> None:
    color  = _STATUS_COLOR.get(status, "#9699a6")
    pct    = int(count / total * 100) if total else 0
    q_str  = f"${quoted:,.0f}" if quoted else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;'
        f'border-bottom:1px solid rgba(255,255,255,0.04)">'
        f'<div style="width:130px;font-size:12px;color:#9699a6;flex-shrink:0">{status}</div>'
        f'<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:4px;height:7px;overflow:hidden">'
        f'<div style="width:{pct}%;height:7px;background:{color};border-radius:4px"></div></div>'
        f'<div style="width:28px;text-align:right;font-size:13px;font-weight:700;color:{color}">{count}</div>'
        f'<div style="width:64px;text-align:right;font-size:11px;color:#6e6f8f">{q_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    from app.pages.page_home_roles import render as _render_roles
    _render_roles()


def render_map():
    # ── Fetch data ────────────────────────────────────────────────────────────
    stats = {}; jobs_by_status = []; recent_jobs = []; monthly_rev = []
    sites_with_coords: list[dict] = []
    all_jobs: list[dict] = []
    try:
        from app.services.crm_db import (
            get_crm_stats, get_jobs_by_status, get_recent_jobs,
            get_monthly_revenue, init_crm_tables, geocode_sites,
            get_sites_with_coords, get_all_jobs,
        )
        init_crm_tables()
        stats           = get_crm_stats()
        jobs_by_status  = get_jobs_by_status()
        recent_jobs     = get_recent_jobs(limit=8)
        monthly_rev     = get_monthly_revenue()
        # Geocode in background (fast — pgeocode is offline lookup)
        geocode_sites()
        sites_with_coords = get_sites_with_coords()
        all_jobs          = get_all_jobs()
    except Exception:
        pass

    today = datetime.date.today().strftime("%B %d, %Y")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:10px 0 12px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:12px">'
        f'<div style="font-size:20px;font-weight:800;color:#d5d8df;letter-spacing:-0.02em">'
        f'Sterling <span style="color:#1AB738">Operations</span></div>'
        f'<div style="font-size:11px;color:#6e6f8f;font-family:\'JetBrains Mono\',monospace">'
        f'{today}</div></div>',
        unsafe_allow_html=True,
    )

    # ── Quick actions ─────────────────────────────────────────────────────────
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
        if st.button("📅  Calendar", use_container_width=True):
            st.session_state.current_page = "calendar"
            st.rerun()

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # ── Map layer toggles ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap">',
        unsafe_allow_html=True,
    )
    tc1, tc2, tc3, tc4, tc5, tc6 = st.columns([1,1,1,1,1,3])
    show_active   = tc1.checkbox("🟢 Active",      value=True,  key="map_active")
    show_inactive = tc2.checkbox("⚪ Inactive",    value=False, key="map_inactive")
    show_hold     = tc3.checkbox("🟡 On Hold",     value=True,  key="map_hold")
    show_jobs     = tc4.checkbox("🔧 Jobs",        value=True,  key="map_jobs")
    show_subs     = tc5.checkbox("🟠 Submittals",  value=True,  key="map_subs")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Build map ─────────────────────────────────────────────────────────────
    layers: list = []
    sites_by_id = {s["site_id"]: s for s in sites_with_coords}

    layers += _site_layers(sites_with_coords, show_active, show_inactive, show_hold)
    if show_jobs:
        layers += _job_layer(sites_by_id, all_jobs)
    if show_subs:
        layers += _submittal_layer(sites_with_coords)

    view = pdk.ViewState(
        latitude=42.8,
        longitude=-72.5,
        zoom=6.2,
        pitch=0,
        bearing=0,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={
            "html": (
                "<div style='font-family:system-ui;font-size:12px;padding:4px 6px'>"
                "<b>{name}</b><br/>{city}, {state}<br/>"
                "<span style='color:#1AB738'>{status}</span>"
                "</div>"
            ),
            "style": {
                "background": "#1a1b2e",
                "border": "1px solid rgba(255,255,255,0.12)",
                "border-radius": "6px",
                "color": "#d5d8df",
            },
        },
    )

    if sites_with_coords:
        st.pydeck_chart(deck, use_container_width=True, height=500)
        geocoded_pct = int(len(sites_with_coords) / max(1, stats.get("sites", 1)) * 100)
        st.markdown(
            f'<div style="font-size:10px;color:#4b4e69;text-align:right;margin-top:2px">'
            f'{len(sites_with_coords)} of {stats.get("sites", 0)} sites mapped '
            f'({geocoded_pct}%) · CartoDB Dark Matter</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Geocoding sites… reload in a moment once zip codes are resolved.")

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:flex;gap:14px;flex-wrap:wrap;margin:8px 0 16px;font-size:11px;color:#9699a6">'
        + "".join(
            f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
            f'background:{c};margin-right:5px;vertical-align:middle"></span>{l}</span>'
            for l, c in [
                ("Active site",   "#1AB738"),
                ("On Hold",       "#ffcb00"),
                ("Inactive",      "#9699a6"),
                ("Need to Schedule", "#e2445c"),
                ("Scheduled job", "#ffcb00"),
                ("In Progress",   "#579bfc"),
                ("Complete",      "#00c875"),
                ("Submittal due", "#fd7e14"),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    # ── KPI row ───────────────────────────────────────────────────────────────
    open_jobs    = stats.get("open_jobs", 0)
    total_sites  = stats.get("sites", 0)
    total_leads  = stats.get("leads", 0)
    quoted_total = stats.get("quoted_total", 0)

    k1, k2, k3, k4 = st.columns(4, gap="small")
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

    # ── Pipeline + Revenue ────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="medium")

    with col_left:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:#9699a6;'
            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Job Pipeline</div>',
            unsafe_allow_html=True,
        )
        if jobs_by_status:
            total_jobs = sum(r.get("cnt", 0) for r in jobs_by_status)
            status_map = {r["job_status"]: r for r in jobs_by_status}
            for s in _STATUS_ORDER:
                if s in status_map:
                    row = status_map[s]
                    _pipeline_bar(s, row["cnt"], total_jobs, row.get("quoted_total", 0))
            for row in jobs_by_status:
                if row["job_status"] not in _STATUS_ORDER:
                    _pipeline_bar(row["job_status"], row["cnt"], total_jobs,
                                  row.get("quoted_total", 0))
        else:
            st.caption("No job data yet.")

    with col_right:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:#9699a6;'
            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Monthly Revenue</div>',
            unsafe_allow_html=True,
        )
        if monthly_rev:
            max_q = max((r.get("quoted", 0) for r in monthly_rev), default=1) or 1
            for row in monthly_rev[-6:]:
                month  = row["scheduled_month"][:3]
                quoted = row.get("quoted", 0)
                cnt    = row.get("job_count", 0)
                pct    = int(quoted / max_q * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04)">'
                    f'<div style="width:30px;font-size:11px;color:#9699a6">{month}</div>'
                    f'<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:4px;'
                    f'height:6px;overflow:hidden">'
                    f'<div style="width:{pct}%;height:6px;background:#1AB738;border-radius:4px"></div></div>'
                    f'<div style="width:60px;text-align:right;font-size:11px;color:#d5d8df">'
                    f'${quoted:,.0f}</div>'
                    f'<div style="width:26px;text-align:right;font-size:10px;color:#6e6f8f">'
                    f'{cnt}j</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No monthly data yet.")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # ── Recent Jobs ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:12px;font-weight:600;color:#9699a6;'
        'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Recent Jobs</div>',
        unsafe_allow_html=True,
    )

    if recent_jobs:
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 1, 1])
        for lbl, col in zip(["Site", "Service", "Status", "Owner", "Quoted"],
                             [h1, h2, h3, h4, h5]):
            col.markdown(
                f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.10em;'
                f'color:#4b4e69;padding-bottom:4px">{lbl}</div>',
                unsafe_allow_html=True,
            )
        for job in recent_jobs:
            jstatus = job.get("job_status", "")
            jcolor  = _STATUS_COLOR.get(jstatus, "#9699a6")
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
            site = job.get("job_site") or "—"
            svc  = job.get("service") or "—"
            c1.markdown(f'<div style="font-size:13px;color:#d5d8df;padding:5px 0">'
                        f'{site[:30]}{"…" if len(site)>30 else ""}</div>',
                        unsafe_allow_html=True)
            c2.markdown(f'<div style="font-size:12px;color:#9699a6;padding:5px 0">'
                        f'{svc[:22]}</div>', unsafe_allow_html=True)
            c3.markdown(f'<div style="padding:5px 0"><span style="background:{jcolor}22;'
                        f'color:{jcolor};padding:2px 7px;border-radius:8px;'
                        f'font-size:11px;font-weight:600">{jstatus or "—"}</span></div>',
                        unsafe_allow_html=True)
            owner = (job.get("owner") or "").split()[0] if job.get("owner") else "—"
            c4.markdown(f'<div style="font-size:11px;color:#9699a6;padding:5px 0">'
                        f'{owner}</div>', unsafe_allow_html=True)
            q = job.get("quoted_amount")
            c5.markdown(f'<div style="font-size:12px;color:#1AB738;padding:5px 0;'
                        f'font-weight:600">{"$"+f"{q:,.0f}" if q else "—"}</div>',
                        unsafe_allow_html=True)

        if st.button("View All Jobs →", key="dash_view_jobs"):
            st.session_state.current_page = "crm_jobs"
            st.rerun()
    else:
        st.caption("No jobs yet.")

    st.markdown(
        '<div style="text-align:center;padding:28px 0 6px;font-size:10px;'
        'color:#3D4D5C;letter-spacing:.08em">'
        'Sterling Stormwater Maintenance Services, Inc &nbsp;·&nbsp; Field Service Platform v1.0'
        '</div>',
        unsafe_allow_html=True,
    )

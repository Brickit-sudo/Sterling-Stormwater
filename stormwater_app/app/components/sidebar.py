"""
app/components/sidebar.py
Sterling Stormwater sidebar — real st.button() per nav item (guaranteed reliable).

The onclick-HTML-proxy approach was unreliable across Streamlit versions.
This version uses native Streamlit widgets styled with CSS — the approach
that was confirmed working before role-based changes were introduced.
"""

from pathlib import Path
import streamlit as st
from app.session import get_session, set_page, get_project, save_project_json

LOGO_PATH = Path("assets/sterling_logo.png")

_FULLREPORT_PAGES = {"setup", "systems", "writeups", "export"}

_SECTION_PAGES = {
    "crm":      {"crm_sites", "crm_clients", "crm_leads", "crm_prospects",
                 "crm_jobs", "crm_comms", "calendar"},
    "finance":  {"crm_invoices", "crm_quotes", "crm_svc_catalog"},
    "reports":  {"photosheet", "setup", "systems", "writeups", "export"},
    "archive":  {"crm_files", "library", "bulk_import", "crm_import"},
    "insights": {"trends", "knowledge_base"},
    "settings": {"google_settings"},
}

_DEFAULT_OPEN = {"reports"}

# Sections visible per role (None = all)
_ROLE_SECTIONS: dict[str, set | None] = {
    "owner":      None,
    "ops":        {"crm", "reports", "archive", "settings"},
    "compliance": {"crm", "reports", "archive", "insights", "settings"},
    "worker":     {"reports"},
}

_ROLE_LABELS = {
    "ops":        "Operations Manager",
    "compliance": "Compliance Manager",
    "owner":      "Owner",
    "worker":     "Worker / Field Tech",
}


# ── Sub-components ────────────────────────────────────────────────────────────

def _sub_label(text: str) -> None:
    st.markdown(
        f'<div style="font-size:10px;color:#4b4e69;padding:6px 4px 1px 8px;'
        f'font-weight:600;letter-spacing:0.09em;text-transform:uppercase'
        f';user-select:none">{text}</div>',
        unsafe_allow_html=True,
    )


def _nav_rule() -> None:
    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0"></div>',
        unsafe_allow_html=True,
    )


def _nav_item(page_key: str, icon: str, label: str, current: str) -> None:
    is_active = current == page_key
    if is_active:
        st.markdown(
            '<div style="'
            'background:linear-gradient(90deg,rgba(26,183,56,0.18) 0%,rgba(26,183,56,0.05) 100%);'
            'border-left:3px solid #1AB738;'
            'border-radius:0 6px 6px 0;margin:1px 2px 1px 0">',
            unsafe_allow_html=True,
        )
    if st.button(f"{icon}  {label}", key=f"nav_{page_key}", use_container_width=True):
        set_page(page_key)
        st.rerun()
    if is_active:
        st.markdown("</div>", unsafe_allow_html=True)


def _section_header(section_key: str, icon: str, label: str, current: str) -> bool:
    """Render a collapsible section header. Returns True if expanded."""
    state_key = f"sidebar_{section_key}_open"

    contains_current = current in _SECTION_PAGES.get(section_key, set())
    if contains_current and not st.session_state.get(state_key, False):
        st.session_state[state_key] = True

    is_open = st.session_state.get(state_key, section_key in _DEFAULT_OPEN)
    chevron = "▼" if is_open else "▶"
    bg      = "rgba(26,183,56,0.08)" if is_open else "rgba(255,255,255,0.04)"
    border  = "#1AB738" if is_open else "transparent"
    color   = "#d5d8df" if is_open else "#9699a6"

    st.markdown(
        f'<div class="sidebar-section-{section_key}" style="'
        f'background:{bg};border-left:3px solid {border};'
        f'border-radius:0 6px 6px 0;margin:2px 2px 2px 0">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<style>'
        f'.sidebar-section-{section_key} + div button {{'
        f'text-align:left !important;font-weight:600 !important;'
        f'color:{color} !important;background:transparent !important;'
        f'border:none !important;}}'
        f'</style>',
        unsafe_allow_html=True,
    )
    if st.button(f"{chevron}  {icon}  {label}", key=f"section_toggle_{section_key}",
                 use_container_width=True):
        st.session_state[state_key] = not is_open
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    return is_open


def _site_chip(meta) -> None:
    site   = meta.site_name   or "New Project"
    client = meta.client_name or ""
    rtype  = meta.report_type or "Inspection"
    client_row = (
        f'<div style="font-size:11px;color:#9699a6;margin-top:1px">{client}</div>'
        if client else ""
    )
    st.markdown(
        '<div style="margin:2px 6px 6px 6px;padding:8px 10px;'
        'background:rgba(255,255,255,0.04);border-radius:6px;'
        'border:1px solid rgba(255,255,255,0.07)">'
        '<div style="font-size:10px;color:#6e6f8f;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px">Active Project</div>'
        f'<div style="font-size:13px;font-weight:600;color:#d5d8df;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{site}</div>'
        f'{client_row}'
        f'<div style="font-size:11px;color:#6e6f8f;margin-top:2px">{rtype}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_sidebar():
    if st.session_state.get("sidebar_hidden"):
        # Slide sidebar off-screen, collapse main margin to full width
        # (expand button is rendered by app.py to avoid duplicate key)
        st.markdown(
            "<style>[data-testid='stSidebar']{"
            "transform:translateX(-230px)!important;"
            "width:0!important;min-width:0!important;"
            "overflow:hidden!important;border-right:none!important}"
            "[data-testid='stMain']{margin-left:0!important}</style>",
            unsafe_allow_html=True,
        )

    with st.sidebar:
        proj    = get_project()
        meta    = proj.meta
        current = get_session("current_page", "home")
        role    = st.session_state.get("user_role", "ops")
        allowed = _ROLE_SECTIONS.get(role)   # None = all sections visible

        def _allow(sec: str) -> bool:
            return allowed is None or sec in allowed

        # ── Logo + collapse ───────────────────────────────────────────────
        c_logo, c_btn = st.columns([4, 1])
        with c_logo:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), use_container_width=True)
        with c_btn:
            if st.button("◀", key="sidebar_collapse_btn", help="Collapse sidebar"):
                st.session_state["sidebar_hidden"] = True
                st.rerun()

        _nav_rule()
        _nav_item("home", "🏠", "Home", current)
        _nav_item("map",  "🗺️", "Site Map", current)
        _nav_rule()

        # ── CRM ───────────────────────────────────────────────────────────
        if _allow("crm") and _section_header("crm", "👥", "CRM", current):
            _nav_item("calendar",      "📅", "Calendar",       current)
            _nav_item("crm_sites",     "🗄️", "Sites",          current)
            _nav_item("crm_clients",   "👤", "Clients",        current)
            _nav_item("crm_leads",     "🎯", "Leads",          current)
            _nav_item("crm_prospects", "📋", "Prospects",      current)
            _nav_item("crm_jobs",      "🔧", "Jobs",           current)
            _nav_item("crm_comms",     "💬", "Communications", current)

        # ── Finance ───────────────────────────────────────────────────────
        if _allow("finance") and _section_header("finance", "💰", "Finance", current):
            _nav_item("crm_invoices",    "🧾", "Invoices",        current)
            _nav_item("crm_quotes",      "💰", "Quote Builder",   current)
            _nav_item("crm_svc_catalog", "🔧", "Service Catalog", current)

        # ── Reports ───────────────────────────────────────────────────────
        if _allow("reports") and _section_header("reports", "📊", "Reports", current):
            _nav_item("photosheet", "📷", "Photosheet", current)
            _sub_label("Full Report")
            _nav_item("setup",    "⚙️",  "Setup",     current)
            _nav_item("systems",  "🔧",  "Systems",   current)
            _nav_item("writeups", "✏️",  "Write-Ups", current)
            _nav_item("export",   "📤",  "Export",    current)

        # ── Archive ───────────────────────────────────────────────────────
        if _allow("archive") and _section_header("archive", "📁", "Archive", current):
            _nav_item("crm_files",   "📁", "File Archive",   current)
            _nav_item("library",     "📚", "Report Library", current)
            _nav_item("bulk_import", "📥", "Bulk Import",    current)
            _nav_item("crm_import",  "📥", "Import Data",    current)

        # ── Insights ──────────────────────────────────────────────────────
        if _allow("insights") and _section_header("insights", "📈", "Insights", current):
            _nav_item("trends",         "📈", "Site History",   current)
            _nav_item("knowledge_base", "📊", "Knowledge Base", current)

        # ── Settings ──────────────────────────────────────────────────────
        if _allow("settings") and _section_header("settings", "⚙️", "Settings", current):
            _nav_item("google_settings", "🔗", "Google Integration", current)

        # ── Active project chip + Save/New (full report pages only) ───────
        if current in _FULLREPORT_PAGES:
            _site_chip(meta)
            _nav_rule()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾  Save", use_container_width=True, type="primary"):
                    save_project_json()
                    try:
                        from app.services.api_client import upsert_report
                        upsert_report(get_project())
                    except Exception:
                        pass
                    st.toast("Project saved", icon="✅")
            with col2:
                if st.button("🔄  New", use_container_width=True):
                    from app.session import ProjectSession
                    st.session_state.project     = ProjectSession()
                    st.session_state.photo_bytes = {}
                    set_page("setup")
                    st.rerun()

        _nav_rule()

        # ── Role indicator (owner-only switcher) ──────────────────────────
        if role == "owner":
            role_options = list(_ROLE_LABELS.keys())
            new_role = st.selectbox(
                "View as",
                options=role_options,
                index=role_options.index(role),
                format_func=lambda r: _ROLE_LABELS[r],
                key="role_switcher_select",
                label_visibility="collapsed",
            )
            if new_role != role:
                st.session_state.user_role = new_role
                st.rerun()
        else:
            st.markdown(
                f'<div style="font-size:11px;color:#6e6f8f;text-align:center;'
                f'padding:2px 0">{_ROLE_LABELS.get(role, role)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            'color:#4b4e69;text-align:center;padding:6px 0 4px;letter-spacing:.06em">'
            'Sterling Reports v1.0</div>',
            unsafe_allow_html=True,
        )

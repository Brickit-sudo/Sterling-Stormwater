"""
app/components/sidebar.py
Sterling Stormwater — monday.com-style collapsible sidebar, persistent across all pages.

Sections (all collapsible):
  CRM      — Sites, Clients, Leads, Prospects, Jobs
  FINANCE  — Invoices, Quote Builder, Service Catalog
  REPORTS  — Home, Photosheet, Full Report (Setup/Systems/Write-Ups/Export)
  ARCHIVE  — File Archive, Report Library, Bulk Import, Import Data
  INSIGHTS — Site History, Knowledge Base
"""

from pathlib import Path
import streamlit as st
from app.session import get_session, set_page, get_project, save_project_json

LOGO_PATH = Path("assets/sterling_logo.png")

_STATUS_COLOR = {"Draft": "#9699a6", "Review": "#ffcb00", "Delivered": "#1AB738"}
_STATUS_ICON  = {"Draft": "●",       "Review": "◑",       "Delivered": "✓"}

_FULLREPORT_PAGES = {"setup", "systems", "writeups", "export"}

_SECTION_PAGES = {
    "crm":      {"crm_sites", "crm_clients", "crm_leads", "crm_prospects", "crm_jobs"},
    "finance":  {"crm_invoices", "crm_quotes", "crm_svc_catalog"},
    "reports":  {"photosheet", "setup", "systems", "writeups", "export"},
    "archive":  {"crm_files", "library", "bulk_import", "crm_import"},
    "insights": {"trends", "knowledge_base"},
}


# ── Sub-components ────────────────────────────────────────────────────────────

def _section_label(text: str) -> None:
    st.markdown(
        f'<div style="font-family:\'Figtree\',sans-serif;font-size:11px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.09em;'
        f'color:#6e6f8f;padding:14px 4px 4px 8px;user-select:none">{text}</div>',
        unsafe_allow_html=True,
    )


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


def _workspace_header(status: str) -> None:
    color = _STATUS_COLOR.get(status, "#9699a6")
    icon  = _STATUS_ICON.get(status, "●")
    st.markdown(
        '<div style="display:flex;align-items:center;gap:8px;padding:10px 8px 8px 8px">'
        '<div style="width:26px;height:26px;border-radius:6px;'
        'background:linear-gradient(135deg,#1AB738,#0f8c28);'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:12px;color:#04140A;font-weight:700;flex-shrink:0">S</div>'
        '<div style="flex:1;min-width:0">'
        '<div style="font-size:13px;font-weight:700;color:#d5d8df;'
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        'Sterling Stormwater</div>'
        f'<div style="font-size:10px;color:{color}">{icon} {status}</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _site_info_chip(meta) -> None:
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

    # Auto-expand if current page belongs to this section
    contains_current = current in _SECTION_PAGES.get(section_key, set())
    if contains_current and not st.session_state.get(state_key, False):
        st.session_state[state_key] = True

    is_open = st.session_state.get(state_key, False)
    chevron = "▼" if is_open else "▶"
    bg      = "rgba(26,183,56,0.08)" if is_open else "rgba(255,255,255,0.04)"
    border  = "#1AB738" if is_open else "transparent"
    color   = "#d5d8df" if is_open else "#9699a6"

    st.markdown(
        f'<div class="sidebar-section-{section_key}" style="'
        f'background:{bg};border-left:3px solid {border};'
        f'border-radius:0 6px 6px 0;margin:2px 2px 2px 0;'
        f'--chev:\'{chevron}\';--sec-color:{color}">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<style>'
        f'.sidebar-section-{section_key} + div button {{'
        f'text-align:left !important;font-weight:600 !important;'
        f'color:{color} !important;background:transparent !important;'
        f'border:none !important;position:relative;'
        f'}}'
        f'.sidebar-section-{section_key} + div button::after {{'
        f'content:"{chevron}";position:absolute;right:12px;'
        f'top:50%;transform:translateY(-50%);font-size:10px;'
        f'color:{color};opacity:0.7;'
        f'}}'
        f'</style>',
        unsafe_allow_html=True,
    )
    if st.button(f"{icon}  {label}", key=f"section_toggle_{section_key}",
                 use_container_width=True):
        st.session_state[state_key] = not is_open
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    return is_open


# ── Main render ───────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        proj    = get_project()
        meta    = proj.meta
        status  = getattr(meta, "status", "Draft")
        current = get_session("current_page", "home")

        # ── Logo / workspace header ───────────────────────────────────────────
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            _workspace_header(status)

        _nav_rule()
        _nav_item("home", "🏠", "Home", current)
        _nav_rule()

        # ═══════════════════════════════════════════════════════════════════
        # CRM
        # ═══════════════════════════════════════════════════════════════════
        if _section_header("crm", "👥", "CRM", current):
            _nav_item("crm_sites",     "🗄️", "Sites",     current)
            _nav_item("crm_clients",   "👤", "Clients",   current)
            _nav_item("crm_leads",     "🎯", "Leads",     current)
            _nav_item("crm_prospects", "📋", "Prospects", current)
            _nav_item("crm_jobs",      "🔧", "Jobs",      current)

        # ═══════════════════════════════════════════════════════════════════
        # FINANCE
        # ═══════════════════════════════════════════════════════════════════
        if _section_header("finance", "💰", "Finance", current):
            _nav_item("crm_invoices",    "🧾", "Invoices",        current)
            _nav_item("crm_quotes",      "💰", "Quote Builder",   current)
            _nav_item("crm_svc_catalog", "🔧", "Service Catalog", current)

        # ═══════════════════════════════════════════════════════════════════
        # REPORTS
        # ═══════════════════════════════════════════════════════════════════
        if _section_header("reports", "📊", "Reports", current):
            _nav_item("photosheet", "📷", "Photosheet", current)

            _sub_label("Full Report")
            _nav_item("setup",    "⚙️",  "Setup",     current)
            _nav_item("systems",  "🔧",  "Systems",   current)
            _nav_item("writeups", "✏️",  "Write-Ups", current)
            _nav_item("export",   "📤",  "Export",    current)

            if current in _FULLREPORT_PAGES:
                _site_info_chip(meta)

        # ═══════════════════════════════════════════════════════════════════
        # ARCHIVE
        # ═══════════════════════════════════════════════════════════════════
        if _section_header("archive", "📁", "Archive", current):
            _nav_item("crm_files",   "📁", "File Archive",   current)
            _nav_item("library",     "📚", "Report Library", current)
            _nav_item("bulk_import", "📥", "Bulk Import",    current)
            _nav_item("crm_import",  "📥", "Import Data",    current)

        # ═══════════════════════════════════════════════════════════════════
        # INSIGHTS
        # ═══════════════════════════════════════════════════════════════════
        if _section_header("insights", "📈", "Insights", current):
            _nav_item("trends",         "📈", "Site History",   current)
            _nav_item("knowledge_base", "📊", "Knowledge Base", current)

        # ── Bottom actions — Full Report workflow only ─────────────────────
        if current in _FULLREPORT_PAGES:
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

        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            'color:#4b4e69;text-align:center;padding:10px 0 4px 0;letter-spacing:0.06em">'
            'Sterling Reports v1.0</div>',
            unsafe_allow_html=True,
        )

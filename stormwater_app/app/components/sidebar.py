"""
app/components/sidebar.py
Sterling Stormwater sidebar — native st.button() nav, CSS-styled.
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
    "data":     {"crm_files", "library", "bulk_import", "crm_import", "sync"},
    "insights": {"trends", "knowledge_base"},
    "admin":    {"google_settings"},
}

_ROLE_SECTIONS: dict[str, set | None] = {
    "owner":      None,
    "ops":        {"crm", "finance", "reports", "data", "admin"},
    "compliance": {"crm", "finance", "reports", "data", "insights"},
    "worker":     {"reports"},
}

_ROLE_LABELS = {
    "ops":        "Operations Manager",
    "compliance": "Compliance Manager",
    "owner":      "Owner",
    "worker":     "Worker / Field Tech",
}


# ── Sub-components ────────────────────────────────────────────────────────────

def _nd(lbl: str) -> None:
    """Section divider with label."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;padding:16px 8px 6px 8px">'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:.11em;'
        f'text-transform:uppercase;color:#5ad4a0;'
        f'font-family:\'JetBrains Mono\',monospace;white-space:nowrap">▪ {lbl}</span>'
        f'<div style="flex:1;height:1px;background:rgba(90,212,160,0.22)"></div></div>',
        unsafe_allow_html=True,
    )


def _nav_rule() -> None:
    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0"></div>',
        unsafe_allow_html=True,
    )


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
        allowed = _ROLE_SECTIONS.get(role)

        def _allow(sec: str) -> bool:
            return allowed is None or sec in allowed

        # ── Logo ─────────────────────────────────────────────────────────────
        if LOGO_PATH.exists():
            st.markdown(
                '<div style="padding:14px 12px 0;border-bottom:none">',
                unsafe_allow_html=True,
            )
            st.image(str(LOGO_PATH), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Collapse button ───────────────────────────────────────────────────
        st.markdown(
            '<style>'
            '[class*="sidebar_collapse_btn"] button {'
            '  width:100%!important;'
            '  border-radius:0!important;'
            '  border-top:1px solid rgba(255,255,255,0.06)!important;'
            '  border-left:none!important;border-right:none!important;border-bottom:none!important;'
            '  background:transparent!important;'
            '  color:#9699a6!important;'
            '  font-size:11px!important;'
            '  font-family:\'JetBrains Mono\',monospace!important;'
            '  letter-spacing:0.06em!important;'
            '  height:28px!important;min-height:28px!important;'
            '  justify-content:flex-end!important;padding-right:10px!important;'
            '  margin-bottom:4px!important;'
            '}'
            '[class*="sidebar_collapse_btn"] button:hover {'
            '  background:rgba(255,255,255,0.05)!important;'
            '  color:#e0e2ea!important;'
            '}'
            '</style>',
            unsafe_allow_html=True,
        )
        if st.button("◀  COLLAPSE", key="sidebar_collapse_btn", use_container_width=True):
            st.session_state["sidebar_hidden"] = True
            st.rerun()

        # ── Active-state CSS for the current page button ──────────────────────
        st.markdown(
            f'<style>'
            f'[data-testid="stSidebar"] [class*="st-key-nav_{current}"] button{{'
            f'background:linear-gradient(90deg,rgba(26,183,56,.18) 0%,rgba(26,183,56,.04) 100%)!important;'
            f'border-left-color:#1AB738!important;'
            f'color:#e8f0f3!important;font-weight:500!important;}}'
            f'</style>',
            unsafe_allow_html=True,
        )

        # ── Nav button helper ─────────────────────────────────────────────────
        def _nb(key: str, label: str) -> None:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                set_page(key)
                st.rerun()

        # ── Nav items ─────────────────────────────────────────────────────────
        _nb("home", "Home")
        _nb("map",  "Site Map")

        if _allow("crm"):
            _nd("Pipeline")
            _nb("calendar",      "Calendar")
            _nb("crm_sites",     "Sites")
            _nb("crm_clients",   "Clients")
            _nb("crm_jobs",      "Jobs")
            _nb("crm_leads",     "Leads")
            _nb("crm_prospects", "Prospects")
            _nb("crm_comms",     "Communications")

        if _allow("finance"):
            _nd("Finance")
            _nb("crm_invoices",    "Invoices")
            _nb("crm_quotes",      "Quote Builder")
            _nb("crm_svc_catalog", "Service Catalog")

        if _allow("reports"):
            _nd("Field Reports")
            _nb("photosheet", "Photosheet")
            _nb("setup",      "Report Setup")
            _nb("systems",    "Systems")
            _nb("writeups",   "Write-Ups")
            _nb("export",     "Export")

        if _allow("data"):
            _nd("Data")
            _nb("crm_files",   "File Archive")
            _nb("library",     "Report Library")
            _nb("bulk_import", "Bulk Import")
            _nb("crm_import",  "CRM Import")
            _nb("sync",        "Drive Sync")

        if _allow("insights"):
            _nd("Insights")
            _nb("trends",         "Site History")
            _nb("knowledge_base", "Knowledge Base")

        if _allow("admin"):
            _nd("Admin")
            _nb("google_settings", "Google Integration")

        # ── Active project chip + Save/New ────────────────────────────────────
        if current in _FULLREPORT_PAGES:
            _site_chip(meta)
            _nav_rule()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save", use_container_width=True, type="primary"):
                    save_project_json()
                    try:
                        from app.services.api_client import upsert_report
                        upsert_report(get_project())
                    except Exception:
                        pass
                    st.toast("Project saved", icon="✅")
            with col2:
                if st.button("New", use_container_width=True):
                    from app.session import ProjectSession
                    st.session_state.project     = ProjectSession()
                    st.session_state.photo_bytes = {}
                    set_page("setup")
                    st.rerun()

        _nav_rule()

        # ── Role indicator ────────────────────────────────────────────────────
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
                f'<div style="text-align:center;padding:4px 0 2px">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:.10em;'
                f'text-transform:uppercase;color:#3d6070;'
                f'font-family:\'JetBrains Mono\',monospace;margin-bottom:2px">Role</div>'
                f'<div style="font-size:11px;color:#8aabb8">{_ROLE_LABELS.get(role, role)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            'color:#3d6070;text-align:center;padding:6px 0 4px;letter-spacing:.06em">'
            'Sterling Reports v1.0</div>',
            unsafe_allow_html=True,
        )

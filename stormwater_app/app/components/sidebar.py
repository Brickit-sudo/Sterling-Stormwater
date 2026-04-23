"""
app/components/sidebar.py
Sterling Stormwater sidebar — flat SVG icon nav.
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

# Sections visible per role (None = all)
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


# ── SVG icon system ───────────────────────────────────────────────────────────

_ICON_PATHS = {
    "home":      ["M2 7.5L8 2l6 5.5V14H10v-3.5H6V14H2V7.5z"],
    "map":       ["M8 1.5C5.51 1.5 3.5 3.51 3.5 6c0 3.75 4.5 8.5 4.5 8.5S12.5 9.75 12.5 6C12.5 3.51 10.49 1.5 8 1.5z", "M8 7.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"],
    "calendar":  ["M1.5 3.5h13v11h-13z", "M5 1.5v4", "M11 1.5v4", "M1.5 7.5h13"],
    "building":  ["M2 14V5l6-3 6 3v9", "M6 14v-4h4v4", "M5.5 6.5h1", "M5.5 9h1", "M9.5 6.5h1", "M9.5 9h1"],
    "person":    ["M8 8a3 3 0 100-6 3 3 0 000 6z", "M2 14.5c0-3.31 2.69-6 6-6s6 2.69 6 6"],
    "leads":     ["M2 8h12", "M9 3l5 5-5 5"],
    "prospects": ["M14 7A6 6 0 112 7a6 6 0 0112 0z", "M10 7H8", "M8 5v4"],
    "jobs":      ["M2 5h12v9H2z", "M5 5V3a1 1 0 011-1h4a1 1 0 011 1v2", "M6 9h4", "M8 7.5v3"],
    "comms":     ["M2 2.5h9v7H8l-3 2.5V9.5H2z", "M11 5h3v5h-1.5l-2 2V10h.5"],
    "invoice":   ["M3 2h10v12H3z", "M6 5.5h4", "M6 8h4", "M6 10.5h3"],
    "quote":     ["M2 2h5v5l-2 3H3L5 7H2V2z", "M9 2h5v5l-2 3h-2l2-3H9V2z"],
    "catalog":   ["M2 3h12v2H2z", "M2 7h12v2H2z", "M2 11h12v2H2z"],
    "photo":     ["M1.5 4.5A1 1 0 012.5 3.5h11a1 1 0 011 1V12a1 1 0 01-1 1H2.5a1 1 0 01-1-1V4.5z", "M5.5 7.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z", "M1.5 10.5l4-3 3 2.5 2.5-2 3 2.5"],
    "newReport": ["M3.5 2h7l2.5 2.5V14h-9.5V2z", "M10.5 2v3h2.5", "M8 6.5v5", "M5.5 9h5"],
    "gear":      ["M8 5.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z", "M8 1v1.5", "M8 13.5V15", "M1 8h1.5", "M13.5 8H15", "M2.636 2.636l1.06 1.06", "M12.304 12.304l1.06 1.06", "M13.364 2.636l-1.06 1.06", "M3.696 12.304l-1.06 1.06"],
    "download":  ["M8 2v9", "M4.5 7.5L8 11l3.5-3.5", "M1.5 13.5h13"],
    "reports":   ["M3.5 2h7l2.5 2.5V14h-9.5V2z", "M10.5 2v3h2.5", "M6 6.5h4", "M6 9h4", "M6 11.5h3"],
    "folder":    ["M2 4.5l2.5-2.5H7l1.5 1.5H14V13H2V4.5z"],
    "import":    ["M8 2v9", "M4.5 7.5L8 11l3.5-3.5", "M2 14h12", "M2 2h2v9H2z", "M12 2h2v9h-2z"],
    "sync":      ["M12.5 4A5.5 5.5 0 003 8", "M3.5 12A5.5 5.5 0 0013 8", "M12.5 4l-2-2", "M12.5 4l2-2", "M3.5 12l-2 2", "M3.5 12l2 2"],
    "trend":     ["M1.5 12.5l4-4 3 2.5 4-5 2 2"],
    "knowledge": ["M3 2h10v12H3z", "M6 5h4", "M6 7.5h4", "M6 10h4", "M6 12.5h3"],
}


def _svg_icon(name: str, size: int = 15, opacity: float = 0.65) -> str:
    paths = _ICON_PATHS.get(name, [])
    path_els = "".join(f'<path d="{p}"/>' for p in paths)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 16 16" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="opacity:{opacity};flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'{path_els}</svg>'
    )


# ── Sub-components ────────────────────────────────────────────────────────────

def _section_divider(label: str) -> None:
    """Flat divider with label — replaces collapsible section headers."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'padding:12px 14px 4px;">'
        f'<span style="font-size:10px;font-weight:700;letter-spacing:0.10em;'
        f'text-transform:uppercase;color:#3d6070;'
        f'font-family:\'JetBrains Mono\',monospace;white-space:nowrap">{label}</span>'
        f'<div style="flex:1;height:1px;background:#1a3545"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _sub_label(text: str) -> None:
    st.markdown(
        f'<div style="font-size:10px;color:#3d6070;padding:6px 4px 1px 8px;'
        f'font-weight:600;letter-spacing:0.09em;text-transform:uppercase'
        f';user-select:none">{text}</div>',
        unsafe_allow_html=True,
    )


def _nav_rule() -> None:
    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0"></div>',
        unsafe_allow_html=True,
    )


def _nav_item(page_key: str, icon_name: str, label: str, current: str) -> None:
    is_active = current == page_key
    icon_html = _svg_icon(icon_name, size=14, opacity=1.0 if is_active else 0.65)
    bg = "linear-gradient(90deg,rgba(26,183,56,0.20) 0%,rgba(26,183,56,0.04) 100%)" if is_active else "transparent"
    border = "3px solid #1AB738" if is_active else "3px solid transparent"
    color = "#e8f0f3" if is_active else "#c5dae2"
    fw = "500" if is_active else "400"

    st.markdown(
        f'<div data-navkey="{page_key}" style="display:flex;align-items:center;gap:10px;'
        f'padding:7px 12px 7px 9px;height:34px;background:{bg};border-left:{border};'
        f'border-radius:0 6px 6px 0;margin:1px 2px 1px 0;color:{color};'
        f'font-size:13px;font-weight:{fw};font-family:\'Figtree\',sans-serif;">'
        f'{icon_html}'
        f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    key = f"nav_{page_key}"
    if st.button("", key=key, use_container_width=True):
        set_page(page_key)
        st.rerun()


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
        allowed = _ROLE_SECTIONS.get(role)   # None = all sections visible

        def _allow(sec: str) -> bool:
            return allowed is None or sec in allowed

        # ── Logo (full-width, 60px tall) ──────────────────────────────────────
        if LOGO_PATH.exists():
            st.markdown(
                '<div style="padding:14px 12px 0;border-bottom:none">',
                unsafe_allow_html=True,
            )
            st.image(str(LOGO_PATH), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Collapse strip below logo ─────────────────────────────────────────
        st.markdown(
            '<style>'
            '/* Collapse button - full width strip */'
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

        # ── Nav: single HTML block + JS-wired hidden buttons ─────────────────
        def _ni(key: str, icon: str, lbl: str) -> str:
            a = current == key
            return (
                f'<div class="sw-nv" data-navkey="{key}" style="display:flex;align-items:center;'
                f'gap:10px;padding:7px 12px 7px 9px;height:34px;cursor:pointer;box-sizing:border-box;'
                f'border-left:{"3px solid #1AB738" if a else "3px solid transparent"};'
                f'background:{"linear-gradient(90deg,rgba(26,183,56,.18) 0%,rgba(26,183,56,.18) 35%,rgba(26,183,56,.04) 100%)" if a else "transparent"};'
                f'border-radius:0 6px 6px 0;margin:1px 2px 1px 0;'
                f'color:{"#e8f0f3" if a else "#c5dae2"};'
                f'font-size:13px;font-weight:{"500" if a else "400"};font-family:Figtree,sans-serif">'
                f'{_svg_icon(icon, 14, 1.0 if a else 0.65)}'
                f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{lbl}</span>'
                f'</div>'
            )

        def _nd(lbl: str) -> str:
            return (
                f'<div style="display:flex;align-items:center;gap:8px;padding:16px 8px 6px 8px">'
                f'<span style="font-size:11px;font-weight:700;letter-spacing:.11em;'
                f'text-transform:uppercase;color:#5ad4a0;'
                f'font-family:\'JetBrains Mono\',monospace;white-space:nowrap">▪ {lbl}</span>'
                f'<div style="flex:1;height:1px;background:rgba(90,212,160,0.22)"></div></div>'
            )

        parts: list[str] = []
        nav_keys: list[str] = []

        def _add(key: str, icon: str, lbl: str) -> None:
            parts.append(_ni(key, icon, lbl))
            nav_keys.append(key)

        _add("home", "home", "Home")
        _add("map",  "map",  "Site Map")

        if _allow("crm"):
            parts.append(_nd("Pipeline"))
            _add("calendar",      "calendar",  "Calendar")
            _add("crm_sites",     "building",  "Sites")
            _add("crm_clients",   "person",    "Clients")
            _add("crm_jobs",      "jobs",      "Jobs")
            _add("crm_leads",     "leads",     "Leads")
            _add("crm_prospects", "prospects", "Prospects")
            _add("crm_comms",     "comms",     "Communications")

        if _allow("finance"):
            parts.append(_nd("Finance"))
            _add("crm_invoices",    "invoice", "Invoices")
            _add("crm_quotes",      "quote",   "Quote Builder")
            _add("crm_svc_catalog", "catalog", "Service Catalog")

        if _allow("reports"):
            parts.append(_nd("Field Reports"))
            _add("photosheet", "photo",     "Photosheet")
            _add("setup",      "newReport", "Report Setup")
            _add("systems",    "gear",      "Systems")
            _add("writeups",   "knowledge", "Write-Ups")
            _add("export",     "download",  "Export")

        if _allow("data"):
            parts.append(_nd("Data"))
            _add("crm_files",   "folder",  "File Archive")
            _add("library",     "reports", "Report Library")
            _add("bulk_import", "import",  "Bulk Import")
            _add("crm_import",  "import",  "CRM Import")
            _add("sync",        "sync",    "Drive Sync")

        if _allow("insights"):
            parts.append(_nd("Insights"))
            _add("trends",         "trend",     "Site History")
            _add("knowledge_base", "knowledge", "Knowledge Base")

        if _allow("admin"):
            parts.append(_nd("Admin"))
            _add("google_settings", "gear", "Google Integration")

        _NAV_CLICK = (
            "var i=event.target.closest('[data-navkey]');"
            "if(!i)return;"
            "var k=i.dataset.navkey;"
            "var c=document.querySelector('[class*=st-key-nav_'+k+']');"
            "if(c){var b=c.querySelector('button');if(b)b.click();}"
        )
        st.markdown(
            f'<div onclick="{_NAV_CLICK}" style="padding:6px 0">'
            + "".join(parts)
            + "</div>",
            unsafe_allow_html=True,
        )

        # Hidden Streamlit trigger buttons — swNav() clicks these via JS
        for _pk in nav_keys:
            if st.button("", key=f"nav_{_pk}"):
                set_page(_pk)
                st.rerun()

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

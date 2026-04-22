"""
app/components/sidebar.py
Sterling Stormwater — monday.com-style sidebar.

Nav is one HTML block (CSS+JS only — zero per-item Streamlit element overhead).
Click routing: HTML onclick → JS → finds off-screen Streamlit button by text → .click()
Off-screen buttons are real Streamlit widgets guaranteed to trigger reruns.
"""

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from app.session import get_session, set_page, get_project, save_project_json

LOGO_PATH = Path("assets/sterling_logo.png")

_FULLREPORT_PAGES = {"setup", "systems", "writeups", "export"}
_SECTION_PAGES = {
    "crm":      {"crm_sites", "crm_clients", "crm_leads", "crm_prospects", "crm_jobs", "crm_comms", "calendar"},
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

# All navigable pages
_ALL_PAGES = [
    "home", "map",
    "crm_sites", "crm_clients", "crm_leads", "crm_prospects", "crm_jobs", "crm_comms", "calendar",
    "google_settings",
    "crm_invoices", "crm_quotes", "crm_svc_catalog",
    "photosheet", "setup", "systems", "writeups", "export",
    "crm_files", "library", "bulk_import", "crm_import",
    "trends", "knowledge_base",
]
_ALL_SECTIONS = ["crm", "finance", "reports", "archive", "insights", "settings"]

# Prefix that makes button text invisible even if CSS fails
_P = "\u200b"  # zero-width space


# ── Nav HTML + CSS ────────────────────────────────────────────────────────────

_NAV_CSS = """<style>
.sw{font-family:'Figtree',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    padding:2px 6px 10px;-webkit-font-smoothing:antialiased}
.sw-row{display:flex;align-items:center;gap:8px;padding:0 8px;height:32px;
    border-radius:6px;cursor:pointer;font-size:13px;color:#9699a6;
    transition:background 100ms,color 100ms;user-select:none;
    white-space:nowrap;overflow:hidden;margin:1px 0}
.sw-row:hover{background:#363a52;color:#d5d8df}
.sw-row.on{background:rgba(26,183,56,0.18);color:#d5d8df;font-weight:500}
.sw-row.sec{font-weight:500;margin:4px 0 1px;height:34px}
.sw-row.i1{padding-left:20px}
.sw-row.i2{padding-left:32px;font-size:12px;height:28px}
.sw-chev{font-size:11px;width:12px;flex-shrink:0}
.sw-ico{font-size:14px;flex-shrink:0;line-height:1}
.sw-body.shut{display:none}.sw-body.open{display:block}
.sw-grp{font-size:10px;font-weight:600;text-transform:uppercase;
    letter-spacing:.1em;color:#4b4e69;padding:6px 8px 2px 32px;user-select:none}
</style>"""


def _row(page: str, icon: str, label: str, current: str, indent: int = 0) -> str:
    cls = "sw-row on" if current == page else "sw-row"
    if indent:
        cls += f" i{indent}"
    return (f'<div class="{cls}" onclick="swN(\'{page}\')">'
            f'<span class="sw-ico">{icon}</span><span>{label}</span></div>')


def _sec(key: str, icon: str, label: str, body: str, open_set: set) -> str:
    is_open = key in open_set
    chev = "▾" if is_open else "▸"
    cls = "sw-body open" if is_open else "sw-body shut"
    return (
        f'<div class="sw-row sec" onclick="swS(\'{key}\')">'
        f'<span class="sw-chev">{chev}</span>'
        f'<span class="sw-ico">{icon}</span><span>{label}</span></div>'
        f'<div class="{cls}">{body}</div>'
    )


def _grp(text: str) -> str:
    return f'<div class="sw-grp">{text}</div>'


def _build_nav(current: str, open_set: set, allowed: set | None = None) -> str:
    def _allow(sec: str) -> bool:
        return allowed is None or sec in allowed

    crm_items = _row("calendar", "📅", "Calendar", current, 1)
    if _allow("crm"):
        crm_items += (
            _row("crm_sites",     "🗄️", "Sites",          current, 1) +
            _row("crm_clients",   "👤", "Clients",        current, 1) +
            _row("crm_leads",     "🎯", "Leads",          current, 1) +
            _row("crm_prospects", "📋", "Prospects",      current, 1) +
            _row("crm_comms",     "💬", "Communications", current, 1)
        )
    crm_items += _row("crm_jobs", "🔧", "Jobs", current, 1)

    finance = (
        _row("crm_invoices",    "🧾", "Invoices",        current, 1) +
        _row("crm_quotes",      "💰", "Quote Builder",   current, 1) +
        _row("crm_svc_catalog", "🔧", "Service Catalog", current, 1)
    )
    reports = (
        _row("photosheet", "📷", "Photosheet", current, 1) +
        _grp("Full Report") +
        _row("setup",    "⚙️",  "Setup",     current, 2) +
        _row("systems",  "🔧",  "Systems",   current, 2) +
        _row("writeups", "✏️",  "Write-Ups", current, 2) +
        _row("export",   "📤",  "Export",    current, 2)
    )
    archive = (
        _row("crm_files",   "📁", "File Archive",   current, 1) +
        _row("library",     "📚", "Report Library", current, 1) +
        _row("bulk_import", "📥", "Bulk Import",    current, 1) +
        _row("crm_import",  "📥", "Import Data",    current, 1)
    )
    insights = (
        _row("trends",         "📈", "Site History",   current, 1) +
        _row("knowledge_base", "📊", "Knowledge Base", current, 1)
    )
    settings = (
        _row("google_settings", "🔗", "Google Integration", current, 1)
    )

    body = _row("home", "🏠", "Home", current)
    body += _row("map", "🗺️", "Site Map", current)
    body += _row("photosheet", "📷", "Photosheet", current) if (allowed is not None and not _allow("reports")) else ""
    if _allow("crm"):
        body += _sec("crm", "👥", "CRM", crm_items, open_set)
    if _allow("finance"):
        body += _sec("finance", "💰", "Finance", finance, open_set)
    if _allow("reports"):
        body += _sec("reports", "📊", "Reports", reports, open_set)
    if _allow("archive"):
        body += _sec("archive", "📁", "Archive", archive, open_set)
    if _allow("insights"):
        body += _sec("insights", "📈", "Insights", insights, open_set)
    if _allow("settings"):
        body += _sec("settings", "⚙️", "Settings", settings, open_set)

    return f'{_NAV_CSS}<div class="sw">{body}</div>'


# ── JS via component iframe ───────────────────────────────────────────────────
# Defines swN/swS on window.parent; they find off-screen hidden Streamlit
# buttons by their ZW-space-prefixed text content and call .click().

_COMM_JS = f"""<script>
(function(){{
  var par = window.parent;
  var P = '{_P}';
  function click(txt) {{
    var btns = par.document.querySelectorAll(
      '[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]');
    for (var i = 0; i < btns.length; i++) {{
      var p = btns[i].querySelector('p');
      if (p && p.textContent === txt) {{ btns[i].click(); return; }}
    }}
  }}
  par.swN = function(page) {{ click(P + 'n:' + page); }};
  par.swS = function(key)  {{ click(P + 's:' + key);  }};
}})();
</script>"""


# ── Sidebar chrome CSS ────────────────────────────────────────────────────────

_CHROME_CSS = """<style>
[data-testid="stSidebar"] .stVerticalBlock{gap:0!important}
[data-testid="stSidebar"] [data-testid="stElementContainer"],
[data-testid="stSidebar"] .element-container{
  margin-top:0!important;margin-bottom:0!important}
/* Hide the JS injector iframe */
[data-testid="stSidebar"] iframe,
[data-testid="stSidebar"] [data-testid="stCustomComponentV1"]{
  height:0!important;min-height:0!important;border:none!important;
  overflow:hidden!important;display:block!important;margin:0!important}
/* Hide hidden nav button zone — positioned off-screen, zero size */
[data-testid="stSidebar"] div:has(#sw-hb-zone) ~ div .stButton>button{
  position:fixed!important;left:-9999px!important;top:-9999px!important;
  width:1px!important;height:1px!important;opacity:0!important;
  pointer-events:none!important;overflow:hidden!important}
[data-testid="stSidebar"] div:has(#sw-hb-zone) ~ div .stButton{
  margin:0!important;padding:0!important;height:0!important;overflow:hidden!important}
[data-testid="stSidebar"] div:has(#sw-hb-zone) ~ div{
  margin:0!important;padding:0!important;height:0!important;overflow:hidden!important}
</style>"""


# ── Site chip ─────────────────────────────────────────────────────────────────

def _site_chip(meta) -> None:
    site   = meta.site_name   or "New Project"
    client = meta.client_name or ""
    rtype  = meta.report_type or "Inspection"
    extra  = (f'<div style="font-size:11px;color:#9699a6;margin-top:1px">{client}</div>'
              if client else "")
    st.markdown(
        '<div style="margin:4px 6px 6px;padding:8px 10px;background:rgba(255,255,255,0.04);'
        'border-radius:6px;border:1px solid rgba(255,255,255,0.07)">'
        '<div style="font-size:10px;color:#4b4e69;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.08em;margin-bottom:2px">Active Project</div>'
        f'<div style="font-size:13px;font-weight:600;color:#d5d8df;white-space:nowrap;'
        f'overflow:hidden;text-overflow:ellipsis">{site}</div>'
        f'{extra}'
        f'<div style="font-size:11px;color:#6e6f8f;margin-top:2px">{rtype}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_sidebar():
    if st.session_state.get("sidebar_hidden"):
        st.markdown(
            "<style>[data-testid='stSidebar']{transform:translateX(-230px)!important;"
            "width:0!important;min-width:0!important;overflow:hidden!important;"
            "border-right:none!important}"
            "[data-testid='stMain']{margin-left:0!important}</style>",
            unsafe_allow_html=True,
        )

    with st.sidebar:
        st.markdown(_CHROME_CSS, unsafe_allow_html=True)

        proj    = get_project()
        meta    = proj.meta
        current = get_session("current_page", "home")

        # Auto-expand section containing active page
        for sec_key, pages in _SECTION_PAGES.items():
            if current in pages:
                st.session_state.setdefault(f"sb_{sec_key}", True)

        open_set = {k for k in _ALL_SECTIONS
                    if st.session_state.get(f"sb_{k}", k in _DEFAULT_OPEN)}

        role = st.session_state.get("user_role", "ops")
        allowed = _ROLE_SECTIONS.get(role)   # None = all sections visible

        # ── Logo + collapse ───────────────────────────────────────────────
        c_logo, c_btn = st.columns([4, 1])
        with c_logo:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), use_container_width=True)
        with c_btn:
            if st.button("◀", key="sidebar_collapse_btn", help="Collapse sidebar"):
                st.session_state["sidebar_hidden"] = True
                st.rerun()

        # ── Nav HTML (one markdown block, no per-item widgets) ────────────
        st.markdown(_build_nav(current, open_set, allowed), unsafe_allow_html=True)

        # ── JS injector via component iframe ─────────────────────────────
        components.html(_COMM_JS, height=0, scrolling=False)

        # ── Active project chip + Save/New (full report only) ─────────────
        if current in _FULLREPORT_PAGES:
            _site_chip(meta)
            st.markdown('<hr style="border-color:rgba(255,255,255,0.06);margin:6px 0">',
                        unsafe_allow_html=True)
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

        # ── Off-screen hidden Streamlit buttons (JS click targets) ────────
        # These MUST come before the role switcher. CSS hides them via the #sw-hb-zone marker.
        st.markdown('<div id="sw-hb-zone"></div>', unsafe_allow_html=True)

        for page in _ALL_PAGES:
            if st.button(f"{_P}n:{page}", key=f"_nb_{page}"):
                set_page(page)
                st.rerun()

        for sec in _ALL_SECTIONS:
            if st.button(f"{_P}s:{sec}", key=f"_ns_{sec}"):
                sk = f"sb_{sec}"
                st.session_state[sk] = not st.session_state.get(sk, sec in _DEFAULT_OPEN)
                st.rerun()

        # ── Role switcher ─────────────────────────────────────────────────
        st.markdown(
            '<div style="margin:8px 6px 0;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06)"></div>',
            unsafe_allow_html=True,
        )
        role_options = list(_ROLE_LABELS.keys())
        role_idx = role_options.index(role) if role in role_options else 0
        new_role = st.selectbox(
            "View as",
            options=role_options,
            index=role_idx,
            format_func=lambda r: _ROLE_LABELS[r],
            key="role_switcher_select",
            label_visibility="collapsed",
        )
        if new_role != role:
            st.session_state.user_role = new_role
            st.rerun()

        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
            'color:#4b4e69;text-align:center;padding:6px 0 6px;letter-spacing:.06em">'
            'Sterling Reports v1.0</div>',
            unsafe_allow_html=True,
        )

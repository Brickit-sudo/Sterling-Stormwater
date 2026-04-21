"""
app/components/topbar.py
Monday.com-style fixed topbar: board title, action buttons, notifications, view tabs.

HTML bug note: st.markdown() treats \n\n as a Markdown block boundary, causing
everything after a blank line to render as raw text. All HTML here uses single
line-breaks only — no blank lines inside any HTML string.
"""

import streamlit as st
from app.session import get_project, get_session

_PAGE_ICONS = {
    "home":           "🏠",
    "photosheet":     "📷",
    "setup":          "⚙️",
    "systems":        "🔧",
    "writeups":       "✏️",
    "export":         "📤",
    "trends":         "📈",
    "library":        "📚",
    "crm_files":      "📁",
    "knowledge_base": "📊",
    "bulk_import":    "📥",
    "sites":          "🗄️",
    "crm_sites":      "🗄️",
    "crm_clients":    "👤",
    "crm_jobs":       "🔧",
    "crm_leads":      "🎯",
    "crm_import":     "📥",
}

_PAGE_TITLES = {
    "home":           "Home",
    "photosheet":     "Photosheet",
    "setup":          "Report Setup",
    "systems":        "Systems",
    "writeups":       "Write-Ups",
    "export":         "Export",
    "trends":         "Site History",
    "library":        "Report Library",
    "crm_files":      "File Archive",
    "knowledge_base": "Knowledge Base",
    "bulk_import":    "Bulk Import",
    "sites":          "Site Database",
    "crm_sites":      "Sites",
    "crm_clients":    "Clients",
    "crm_jobs":       "Jobs",
    "crm_leads":      "Leads",
    "crm_import":     "CRM Import",
}

_PAGE_VIEWS = {
    "home":           [("🏠", "Dashboard"), ("📁", "File Archive")],
    "photosheet":     [("📷", "Upload"), ("🗂️", "Organize"), ("✏️", "Caption"), ("👁️", "Review")],
    "setup":          [("⚙️", "Site Info"), ("📋", "Report Settings")],
    "systems":        [("🔧", "All Systems"), ("➕", "Add System")],
    "writeups":       [("✏️", "Write-Ups"), ("🏷️", "Conditions")],
    "export":         [("👁️", "Preview"), ("📤", "Generate")],
    "trends":         [("📈", "History"), ("📊", "Analytics")],
    "library":        [("📚", "Reports"), ("🔍", "Search")],
    "crm_files":      [("📁", "Files"), ("⬆️", "Upload")],
    "knowledge_base": [("📖", "Browse"), ("🔍", "Search")],
    "bulk_import":    [("📥", "Import"), ("📋", "History")],
    "sites":          [("🗄️", "All Sites"), ("➕", "Add Site"), ("📊", "Analytics")],
    "crm_sites":      [("🗄️", "All Sites"), ("➕", "Add Site")],
    "crm_clients":    [("👤", "All Clients"), ("➕", "Add Contact")],
    "crm_jobs":       [("🔧", "All Jobs"), ("📅", "Scheduled"), ("✅", "Complete")],
    "crm_leads":      [("🎯", "Pipeline"), ("📊", "By Activity")],
    "crm_import":     [("📥", "Import"), ("📊", "Stats")],
}

_STATUS_COLOR = {
    "Draft":     "#9699a6",
    "Review":    "#ffcb00",
    "Delivered": "#1AB738",
}

_FULLREPORT_PAGES = {"setup", "systems", "writeups", "export", "trends"}


def _compute_notif_count(current_page: str) -> int:
    if current_page not in _FULLREPORT_PAGES:
        return 0
    try:
        proj  = get_project()
        count = 0
        if not proj.meta.site_name:
            count += 1
        if not proj.meta.client_name:
            count += 1
        if not proj.meta.report_date:
            count += 1
        for sys in proj.systems:
            if sys.entry_id not in proj.write_ups:
                count += 1
        return count
    except Exception:
        return 0


def render_topbar() -> str:
    """
    Render the fixed monday.com topbar + view-tabs strip.
    Returns the currently active view label.
    """
    current_page = get_session("current_page", "home")
    icon         = _PAGE_ICONS.get(current_page, "📋")
    title        = _PAGE_TITLES.get(current_page, "Board")
    views        = _PAGE_VIEWS.get(current_page, [("📋", title)])

    # Project context (safe on all pages)
    try:
        proj   = get_project()
        site   = proj.meta.site_name   or ""
        client = proj.meta.client_name or ""
        status = getattr(proj.meta, "status", "Draft")
    except Exception:
        site, client, status = "", "", "Draft"

    subtitle     = site + ("  ·  " + client if site and client else "")
    notif_count  = _compute_notif_count(current_page)
    status_color = _STATUS_COLOR.get(status, "#9699a6")

    notif_badge = (
        f'<span class="monday-notif-badge">{notif_count}</span>'
        if notif_count > 0 else ""
    )
    status_pill = (
        f'<span class="monday-status-pill" '
        f'style="background:{status_color}20;color:{status_color};'
        f'border:1px solid {status_color}40">'
        f'{status}</span>'
    ) if current_page in _FULLREPORT_PAGES else ""

    subtitle_span = (
        f'<span class="monday-board-subtitle">{subtitle}</span>'
    ) if subtitle else ""

    # ── Build view tabs HTML (no blank lines) ─────────────────────────────
    view_key    = f"_topbar_view_{current_page}"
    if view_key not in st.session_state:
        st.session_state[view_key] = views[0][1] if views else title
    active_view = st.session_state[view_key]

    tabs_html = ""
    for tab_icon, tab_label in views:
        active_cls  = " active" if tab_label == active_view else ""
        tabs_html  += (
            f'<span class="monday-view-tab{active_cls}">'
            f'<span class="monday-view-tab-icon">{tab_icon}</span>'
            f'{tab_label}</span>'
        )
    tabs_html += '<span class="monday-view-tab-add" title="New View">+</span>'

    # ── Topbar HTML — NO blank lines (Markdown block-boundary bug) ────────
    topbar_html = (
        '<div class="monday-topbar">'
        f'<div class="monday-board-icon">{icon}</div>'
        f'<span class="monday-board-title">{title}</span>'
        f'{status_pill}'
        f'{subtitle_span}'
        '<div class="monday-topbar-divider"></div>'
        '<div class="monday-topbar-actions">'
        '<span class="monday-action-btn">🔀 Sequences</span>'
        '<span class="monday-action-btn">⚡ Automate</span>'
        '<span class="monday-action-btn">🔗 Integrate</span>'
        '<div class="monday-topbar-divider"></div>'
        f'<div class="monday-notif-btn" title="Notifications">🔔{notif_badge}</div>'
        '<div class="monday-notif-btn" title="Inbox">📥</div>'
        '<div class="monday-topbar-divider"></div>'
        '<span class="monday-action-btn green">💾 Save</span>'
        '<div class="monday-avatar" title="Sterling Stormwater">BR</div>'
        '</div>'
        '</div>'
        f'<div class="monday-view-tabs">{tabs_html}</div>'
    )

    st.markdown(topbar_html, unsafe_allow_html=True)

    # ── Hidden Streamlit buttons to capture view tab clicks ───────────────
    cols = st.columns(len(views), gap="small")
    for i, (_, tab_label) in enumerate(views):
        with cols[i]:
            if st.button(tab_label, key=f"_vtab_{current_page}_{i}",
                         use_container_width=True):
                st.session_state[view_key] = tab_label
                st.rerun()

    # Push the trigger buttons off-screen
    st.markdown(
        '<style>'
        '[class*="stkey__vtab_"] button {'
        'opacity:0!important;height:0!important;padding:0!important;'
        'margin:0!important;border:none!important;min-height:0!important;'
        'overflow:hidden!important;pointer-events:none!important;}'
        '</style>',
        unsafe_allow_html=True,
    )

    return active_view

"""
Stormwater Report Generator
Main entry point — run with: streamlit run app.py
"""

import streamlit as st
from app.session import init_session, get_session
from app.components.sidebar import render_sidebar
from app.components.styles import inject_styles
from app.components.topbar import render_topbar
from app.pages import (
    page_setup,
    page_systems,
    page_writeups,
    page_export,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sterling Report Generator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ────────────────────────────────────────────────────────────
inject_styles()

# ── Database init ─────────────────────────────────────────────────────────────
try:
    from app.services.db import init_db, init_local_user
    init_db()
    init_local_user("brolfe@sterlingstormwater.com", "changeme123", "B. Rolfe")
except Exception:
    pass

try:
    from app.services.crm_db import init_crm_tables
    init_crm_tables()
except Exception:
    pass

# ── Session bootstrap ─────────────────────────────────────────────────────────
init_session()

# ── Auth gate — sidebar NOT shown on login screen ────────────────────────────
if not st.session_state.get("token"):
    from app.pages import page_login
    page_login.render()
    st.stop()

# ── Universal sidebar — always visible after login ───────────────────────────
render_sidebar()

# ── Floating expand button when sidebar is collapsed ─────────────────────────
if st.session_state.get("sidebar_hidden", False):
    # CSS pins the button to top-left; Streamlit key class pattern: stkey__{key}
    st.markdown(
        "<style>"
        "[class*='sidebar_expand_btn'] button,"
        "[data-testid*='sidebar_expand_btn'] button{"
        "  position:fixed!important;"
        "  top:8px!important;left:8px!important;"
        "  z-index:1100!important;"
        "  width:36px!important;height:36px!important;"
        "  min-height:0!important;padding:4px!important;"
        "  font-size:14px!important;"
        "  background:var(--bg-surface)!important;"
        "  border:1px solid var(--border-default)!important;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )
    if st.button("▶", key="sidebar_expand_btn", help="Expand sidebar"):
        st.session_state["sidebar_hidden"] = False
        st.rerun()

# ── Flat page router — current_page drives everything ────────────────────────
current_page = get_session("current_page", "home")

# Topbar on every page except Home
if current_page != "home":
    render_topbar()

PAGE_MAP = {
    "home":     lambda: __import__("app.pages.page_landing",    fromlist=["render"]).render(),
    "photosheet": lambda: __import__("app.pages.page_photosheet", fromlist=["render"]).render(),
    "setup":    page_setup.render,
    "systems":  page_systems.render,
    "writeups": page_writeups.render,
    "export":   page_export.render,
    "trends":         lambda: __import__("app.pages.page_trends",         fromlist=["render"]).render(),
    "library":        lambda: __import__("app.pages.page_library",        fromlist=["render"]).render(),
    "crm_files":      lambda: __import__("app.pages.page_crm_files",      fromlist=["render"]).render(),
    "knowledge_base": lambda: __import__("app.pages.page_knowledge_base", fromlist=["render"]).render(),
    "bulk_import":    lambda: __import__("app.pages.page_bulk_import",    fromlist=["render"]).render(),
    "sites":          lambda: __import__("app.pages.page_sites",          fromlist=["render"]).render(),
    "crm_sites":      lambda: __import__("app.pages.page_crm_sites",      fromlist=["render"]).render(),
    "crm_clients":    lambda: __import__("app.pages.page_crm_clients",    fromlist=["render"]).render(),
    "crm_jobs":       lambda: __import__("app.pages.page_crm_jobs",       fromlist=["render"]).render(),
    "crm_leads":      lambda: __import__("app.pages.page_crm_leads",      fromlist=["render"]).render(),
    "crm_import":       lambda: __import__("app.pages.page_crm_import",         fromlist=["render"]).render(),
    "crm_invoices":     lambda: __import__("app.pages.page_crm_invoices",       fromlist=["render"]).render(),
    "crm_prospects":    lambda: __import__("app.pages.page_crm_prospects",      fromlist=["render"]).render(),
    "crm_quotes":       lambda: __import__("app.pages.page_crm_quotes",         fromlist=["render"]).render(),
    "crm_svc_catalog":  lambda: __import__("app.pages.page_crm_service_catalog",fromlist=["render"]).render(),
    "crm_comms":        lambda: __import__("app.pages.page_crm_comms",          fromlist=["render"]).render(),
    "calendar":         lambda: __import__("app.pages.page_calendar",           fromlist=["render"]).render(),
    "google_settings":  lambda: __import__("app.pages.page_google_settings",    fromlist=["render"]).render(),
}

PAGE_MAP.get(current_page, PAGE_MAP["home"])()

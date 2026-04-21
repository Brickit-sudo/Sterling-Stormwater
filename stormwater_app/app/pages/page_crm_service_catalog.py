"""
app/pages/page_crm_service_catalog.py
Service Catalog — manage standard services used in quotes and invoices.
"""
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.api_client import (
    get_all_service_items, create_service_item,
    update_service_item, delete_service_item,
)

_CATEGORIES = ["Inspection", "Maintenance", "JetVac", "Compliance", "Other"]
_UNITS = ["visit", "ea", "hr", "ton", "day", "lump sum"]
_CAT_COLOR = {
    "Inspection":  "#579bfc",
    "Maintenance": "#1AB738",
    "JetVac":      "#ffcb00",
    "Compliance":  "#a25ddc",
    "Other":       "#9699a6",
}


def _cat_badge(cat: str) -> str:
    color = _CAT_COLOR.get(cat, "#9699a6")
    return (f'<span style="background:{color}20;color:{color};padding:2px 8px;'
            f'border-radius:6px;font-size:11px;font-weight:500">{cat or "—"}</span>')


def _service_form(prefix: str, existing: dict | None = None) -> dict | None:
    e = existing or {}
    with st.form(key=f"svc_form_{prefix}"):
        c1, c2 = st.columns(2)
        with c1:
            name  = st.text_input("Service Name *", value=e.get("name", ""))
            desc  = st.text_area("Description",    value=e.get("description", "") or "", height=60)
        with c2:
            cat   = st.selectbox("Category", _CATEGORIES,
                                 index=_CATEGORIES.index(e.get("category", "Inspection"))
                                 if e.get("category") in _CATEGORIES else 0)
            unit  = st.selectbox("Unit", _UNITS,
                                 index=_UNITS.index(e.get("unit", "visit"))
                                 if e.get("unit") in _UNITS else 0)
            price = st.number_input("Default Price ($)", min_value=0.0, step=25.0,
                                    value=float(e.get("default_unit_price") or 0.0))
        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not name.strip():
                st.error("Service name is required.")
                return None
            return {
                "name": name.strip(),
                "description": desc.strip() or None,
                "category": cat,
                "unit": unit,
                "default_unit_price": price or None,
            }
    return None


def render():
    section_header("Service Catalog", "Standard services used in quotes and invoices.")

    # ── Add button ────────────────────────────────────────────────────────────
    col_hdr, col_btn = st.columns([6, 2])
    with col_btn:
        if st.button("➕ Add Service", use_container_width=True):
            st.session_state["svc_add"] = not st.session_state.get("svc_add", False)

    if st.session_state.get("svc_add"):
        with st.container(border=True):
            st.markdown("**New Service**")
            result = _service_form("add")
            if result:
                created = create_service_item(result)
                if created:
                    st.session_state["svc_add"] = False
                    st.toast(f'Added: {result["name"]}', icon="✅")
                    st.rerun()
                else:
                    st.error("Failed — is the backend running?")

    # ── Fetch ─────────────────────────────────────────────────────────────────
    items = get_all_service_items()

    if not items:
        st.info("No services in catalog yet. Add one above or run the invoice import to auto-seed.", icon="🔧")
        return

    st.caption(f"{len(items)} services in catalog")
    st.markdown("---")

    # ── Group by category ─────────────────────────────────────────────────────
    by_cat: dict[str, list] = {}
    for item in items:
        cat = item.get("category") or "Other"
        by_cat.setdefault(cat, []).append(item)

    for cat in _CATEGORIES:
        cat_items = by_cat.get(cat, [])
        if not cat_items:
            continue

        st.markdown(
            f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.09em;color:#6e6f8f;padding:10px 0 4px 0">{cat}</div>',
            unsafe_allow_html=True,
        )

        for item in cat_items:
            sid      = str(item["service_id"])
            edit_key = f"svc_edit_{sid}"
            del_key  = f"svc_del_{sid}"

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
                with c1:
                    st.markdown(
                        f'**{item["name"]}** &nbsp; ' + _cat_badge(item.get("category", "")),
                        unsafe_allow_html=True,
                    )
                    if item.get("description"):
                        st.caption(item["description"])
                with c2:
                    price = item.get("default_unit_price")
                    st.markdown(
                        f'<span style="color:#1AB738;font-weight:700;font-size:15px">'
                        f'{"$"+f"{float(price):,.2f}" if price else "—"}</span>',
                        unsafe_allow_html=True,
                    )
                    if item.get("unit"):
                        st.caption(f"per {item['unit']}")
                with c3:
                    if st.button("✏️ Edit", key=f"svc_e_{sid}", use_container_width=True):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                with c4:
                    if st.button("🗑️", key=f"svc_d_{sid}", use_container_width=True):
                        st.session_state[del_key] = True

                if st.session_state.get(edit_key):
                    with st.container(border=True):
                        result = _service_form(f"edit_{sid}", existing=item)
                        if result:
                            updated = update_service_item(sid, result)
                            if updated:
                                st.session_state[edit_key] = False
                                st.toast("Updated!", icon="✅")
                                st.rerun()

                if st.session_state.get(del_key):
                    st.warning(f'Delete **{item["name"]}**?')
                    dd1, dd2, _ = st.columns([1, 1, 5])
                    with dd1:
                        if st.button("Yes", key=f"svc_dconf_{sid}", type="primary"):
                            if delete_service_item(sid):
                                st.session_state.pop(del_key, None)
                                st.rerun()
                    with dd2:
                        if st.button("No", key=f"svc_dcancel_{sid}"):
                            st.session_state.pop(del_key, None)
                            st.rerun()

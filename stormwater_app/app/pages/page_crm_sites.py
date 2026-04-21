"""
app/pages/page_crm_sites.py
CRM — Sites Directory. Search, view, add, edit, delete sites.
"""
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.crm_db import (
    get_all_crm_sites, upsert_site, delete_site,
    get_jobs_for_site, init_crm_tables,
)
from app.session import set_page

_STATES    = ["ME","MA","NH","VT","RI","CT","NY","NJ","PA","MD","Other"]
_MONTHS    = ["January","February","March","April","May","June",
              "July","August","September","October","November","December",""]
_STATUSES  = ["Active","Inactive","On Hold",""]


def _systems_count(systems_str: str) -> int:
    if not systems_str:
        return 0
    return len([s for s in systems_str.split(",") if s.strip()])


def _badge(text: str, bg: str = "#30324e", color: str = "#9699a6") -> str:
    return (f'<span style="background:{bg};color:{color};padding:1px 7px;'
            f'border-radius:10px;font-size:11px;font-weight:500">{text}</span>')


def _site_form(prefix: str, existing: dict | None = None) -> dict | None:
    e = existing or {}
    with st.form(key=f"site_form_{prefix}"):
        c1, c2 = st.columns(2)
        with c1:
            name    = st.text_input("Site Name *",   value=e.get("name",""))
            address = st.text_input("Address",       value=e.get("address",""))
            city    = st.text_input("City",          value=e.get("city",""))
            state   = st.selectbox("State", _STATES,
                                   index=_STATES.index(e.get("state","ME")) if e.get("state","ME") in _STATES else 0)
            county  = st.text_input("County",        value=e.get("county",""))
            zipcode = st.text_input("ZIP",           value=e.get("zip",""))
        with c2:
            managed_by    = st.text_input("Managed By",    value=e.get("managed_by",""))
            contact       = st.text_input("Contact Person",value=e.get("contact",""))
            email         = st.text_input("Email",         value=e.get("email",""))
            phone         = st.text_input("Phone",         value=e.get("phone",""))
            client_id     = st.text_input("Client ID (SSC-XXXX)", value=e.get("client_id",""))
            service_month = st.selectbox("Service Month", _MONTHS,
                                         index=_MONTHS.index(e.get("service_month","")) if e.get("service_month","") in _MONTHS else 0)
        systems        = st.text_input("BMP Systems (comma-separated)", value=e.get("systems",""))
        gdrive_url     = st.text_input("Google Drive URL", value=e.get("gdrive_url",""))
        c3, c4 = st.columns(2)
        with c3:
            contract_start = st.text_input("Contract Start (YYYY-MM-DD)", value=e.get("contract_start",""))
            submittal_due  = st.text_input("Submittal Due Date",           value=e.get("submittal_due_date",""))
        with c4:
            contract_end = st.text_input("Contract End (YYYY-MM-DD)", value=e.get("contract_end",""))
            budget       = st.number_input("Budget ($)", min_value=0.0, step=100.0,
                                           value=float(e.get("budget") or 0))
        status = st.selectbox("Status", _STATUSES,
                              index=_STATUSES.index(e.get("status","")) if e.get("status","") in _STATUSES else 0)
        notes  = st.text_area("Notes", value=e.get("notes",""), height=80)
        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not name.strip():
                st.error("Site name is required.")
                return None
            import uuid, re
            site_id = e.get("site_id") or f"SSW-{str(uuid.uuid4())[:8].upper()}"
            return {
                "site_id": site_id, "name": name.strip(),
                "address": address, "city": city, "state": state,
                "county": county, "zip": zipcode, "systems": systems,
                "contact": contact, "client_id": client_id or None,
                "managed_by": managed_by, "email": email, "phone": phone,
                "gdrive_url": gdrive_url, "service_month": service_month,
                "submittal_due_date": submittal_due, "contract_start": contract_start,
                "contract_end": contract_end, "budget": budget or None,
                "status": status, "notes": notes,
            }
    return None


def render():
    init_crm_tables()
    section_header("Sites", "All client sites — search, view, and manage.")

    # ── Filter row ────────────────────────────────────────────────────────────
    col_s, col_f1, col_f2, col_f3, col_add = st.columns([4, 2, 2, 2, 2])
    with col_s:
        search = st.text_input("🔍 Search", placeholder="Site name, city, managed by…",
                               label_visibility="collapsed", key="crm_sites_search")
    with col_f1:
        state_opts = ["All States"] + _STATES
        state_f = st.selectbox("State", state_opts, label_visibility="collapsed",
                               key="crm_sites_state")
    with col_f2:
        status_opts = ["All Status"] + [s for s in _STATUSES if s]
        status_f = st.selectbox("Status", status_opts, label_visibility="collapsed",
                                key="crm_sites_status")
    with col_f3:
        month_opts = ["All Months"] + [m for m in _MONTHS if m]
        month_f = st.selectbox("Month", month_opts, label_visibility="collapsed",
                               key="crm_sites_month")
    with col_add:
        if st.button("➕ Add Site", use_container_width=True):
            st.session_state["crm_site_add"] = not st.session_state.get("crm_site_add", False)

    # ── Add form ──────────────────────────────────────────────────────────────
    if st.session_state.get("crm_site_add"):
        with st.container(border=True):
            st.markdown("**New Site**")
            result = _site_form("add")
            if result:
                upsert_site(result)
                st.session_state["crm_site_add"] = False
                st.toast("Site added!", icon="✅")
                st.rerun()

    # ── Fetch + filter ────────────────────────────────────────────────────────
    state_filter  = "" if state_f  == "All States"  else state_f
    status_filter = "" if status_f == "All Status"  else status_f
    month_filter  = "" if month_f  == "All Months"  else month_f
    sites = get_all_crm_sites(search=search, state=state_filter)
    if status_filter:
        sites = [s for s in sites if (s.get("status") or "") == status_filter]
    if month_filter:
        sites = [s for s in sites if (s.get("service_month") or "") == month_filter]

    # ── Summary metrics ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Showing", len(sites))
    states_present = set(s.get("state") for s in sites if s.get("state"))
    c2.metric("States", len(states_present))
    active   = sum(1 for s in sites if s.get("status") == "Active")
    inactive = sum(1 for s in sites if s.get("status") == "Inactive")
    c3.metric("Active", active)
    c4.metric("Inactive", inactive)
    st.markdown("---")

    if not sites:
        st.info("No sites found. Add your first site above or import from Monday.com data.", icon="🗄️")
        return

    # ── Site list ─────────────────────────────────────────────────────────────
    for site in sites:
        sid       = site["site_id"]
        n_systems = _systems_count(site.get("systems",""))
        edit_key  = f"crm_site_edit_{sid}"
        del_key   = f"crm_site_del_{sid}"

        with st.container(border=True):
            # Header row
            c1, c2, c3 = st.columns([6, 3, 3])
            with c1:
                st.markdown(
                    f'**{site["name"]}** &nbsp; '
                    + _badge(sid, "#1AB73815", "#1AB738"),
                    unsafe_allow_html=True,
                )
                loc = ", ".join(filter(None, [site.get("city"), site.get("state")]))
                if loc:
                    st.caption(f"📍 {loc}")
            with c2:
                if site.get("managed_by"):
                    st.caption(f"👤 {site['managed_by']}")
                if site.get("service_month"):
                    st.caption(f"📅 {site['service_month']}")
            with c3:
                if n_systems:
                    st.caption(f"🔧 {n_systems} BMP{'s' if n_systems != 1 else ''}")
                if site.get("contact"):
                    st.caption(f"📞 {site['contact']}")

            # Detail expander
            with st.expander("View Details & Jobs", expanded=False):
                d1, d2 = st.columns(2)
                with d1:
                    if site.get("address"):
                        st.markdown(f"**Address:** {site['address']}")
                    if site.get("email"):
                        st.markdown(
                            f'**Email:** <a href="mailto:{site["email"]}" '
                            f'style="color:#1AB738">{site["email"]}</a>',
                            unsafe_allow_html=True,
                        )
                    if site.get("phone"):
                        st.markdown(
                            f'**Phone:** <a href="tel:{site["phone"]}" '
                            f'style="color:#1AB738">{site["phone"]}</a>',
                            unsafe_allow_html=True,
                        )
                    if site.get("gdrive_url"):
                        st.markdown(
                            f'<a href="{site["gdrive_url"]}" target="_blank" '
                            f'style="color:#1AB738">📂 Google Drive</a>',
                            unsafe_allow_html=True,
                        )
                with d2:
                    if site.get("contract_start") or site.get("contract_end"):
                        st.markdown(
                            f"**Contract:** {site.get('contract_start','?')} → {site.get('contract_end','?')}"
                        )
                    if site.get("submittal_due_date"):
                        st.markdown(f"**Submittal Due:** {site['submittal_due_date']}")
                    if site.get("budget"):
                        st.markdown(f"**Budget:** ${site['budget']:,.0f}")
                    if site.get("notes"):
                        st.markdown(f"**Notes:** {site['notes']}")

                # Recent jobs
                jobs = get_jobs_for_site(sid)
                if jobs:
                    st.markdown("**Recent Jobs**")
                    import pandas as pd
                    df_j = pd.DataFrame(jobs)[["job_site","service","job_status","scheduled_date","owner","quoted_amount"]]
                    df_j.columns = ["Site","Service","Status","Date","Owner","Quoted"]
                    st.dataframe(df_j.head(5), use_container_width=True, hide_index=True)
                else:
                    st.caption("No jobs linked to this site yet.")

            # Action buttons
            ba1, ba2, ba3, ba4, _ = st.columns([1, 1, 1, 1, 3])
            with ba1:
                if st.button("✏️ Edit", key=f"edit_btn_{sid}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
            with ba2:
                if st.button("📋 Report", key=f"report_btn_{sid}", use_container_width=True):
                    st.session_state["import_extracted"] = {
                        "site_name": site["name"],
                        "site_address": site.get("address",""),
                        "prepared_by": "",
                        "inspection_date": "",
                        "report_type": "Inspection",
                        "system_types": [s.strip() for s in (site.get("systems") or "").split(",") if s.strip()],
                        "raw_summary": "",
                    }
                    set_page("setup")
                    st.rerun()
            with ba3:
                if st.button("💰 Quote", key=f"quote_btn_{sid}", use_container_width=True):
                    st.session_state["new_quote_site_id"] = sid
                    set_page("crm_quotes")
                    st.rerun()
            with ba4:
                if st.button("🗑️", key=f"del_btn_{sid}", use_container_width=True):
                    st.session_state[del_key] = True

            # Edit form
            if st.session_state.get(edit_key):
                with st.container(border=True):
                    st.markdown("**Edit Site**")
                    result = _site_form(f"edit_{sid}", existing=site)
                    if result:
                        upsert_site(result)
                        st.session_state[edit_key] = False
                        st.toast("Site updated!", icon="✅")
                        st.rerun()

            # Delete confirm
            if st.session_state.get(del_key):
                st.warning(f"Delete **{site['name']}**? This cannot be undone.")
                cc1, cc2, _ = st.columns([1, 1, 5])
                with cc1:
                    if st.button("Yes, delete", key=f"del_confirm_{sid}", type="primary"):
                        delete_site(sid)
                        st.session_state.pop(del_key, None)
                        st.rerun()
                with cc2:
                    if st.button("Cancel", key=f"del_cancel_{sid}"):
                        st.session_state.pop(del_key, None)
                        st.rerun()

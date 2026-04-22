"""
app/pages/page_crm_leads.py
CRM — Leads Pipeline. Track prospects and follow-ups.
"""
import uuid
import hashlib
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.crm_db import (
    get_all_leads, upsert_lead, delete_lead,
    get_lead_activities, init_crm_tables,
)
from app.session import set_page

_STATES   = ["ME","MA","NH","VT","RI","CT","NY","NJ","PA","MD","Other",""]
_ACTIVITY_COLORS = {
    "Follow Up":    ("#579bfc20", "#579bfc"),
    "Add Info":     ("#9699a620", "#9699a6"),
    "Complete Work":("#1AB73820", "#1AB738"),
    "Check-Email":  ("#ffcb0020", "#ffcb00"),
    "MOS":          ("#a25ddc20", "#a25ddc"),
    "Processing...":("#e2445c20", "#e2445c"),
}


def _activity_badge(act: str) -> str:
    bg, col = _ACTIVITY_COLORS.get(act, ("#30324e","#9699a6"))
    return (f'<span style="background:{bg};color:{col};padding:2px 8px;'
            f'border-radius:8px;font-size:11px;font-weight:500">{act or "—"}</span>')


def _state_badge(state: str) -> str:
    return (f'<span style="background:#30324e;color:#9699a6;padding:1px 6px;'
            f'border-radius:6px;font-size:11px">{state}</span>') if state else ""


def _lead_id_from_name(name: str) -> str:
    h = hashlib.md5(name.lower().encode()).hexdigest()[:8].upper()
    return f"SWL-{h}"


def _lead_form(prefix: str, existing: dict | None = None) -> dict | None:
    e = existing or {}
    with st.form(key=f"lead_form_{prefix}"):
        c1, c2 = st.columns(2)
        with c1:
            name     = st.text_input("Lead Name *",      value=e.get("name",""))
            email    = st.text_input("Email",             value=e.get("email",""))
            phone    = st.text_input("Phone",             value=e.get("phone",""))
            location = st.text_input("Location",          value=e.get("location",""))
            city     = st.text_input("City",              value=e.get("city",""))
        with c2:
            state        = st.selectbox("State", _STATES,
                                        index=_STATES.index(e.get("state","ME")) if e.get("state","ME") in _STATES else 0)
            services     = st.text_input("Services (INSP/MAINT)",value=e.get("services",""))
            next_activity= st.text_input("Next Activity",        value=e.get("next_activity","Follow Up"))
            poc          = st.text_input("POC / Owner",          value=e.get("poc",""))
            contact_name = st.text_input("Contact Name",         value=e.get("contact_name",""))
        c3, c4 = st.columns(2)
        with c3:
            total    = st.number_input("Total ($)", min_value=0.0, step=100.0,
                                       value=float(e.get("total_amount") or 0))
            deadline = st.text_input("Submittal Deadline", value=e.get("submittal_deadline",""))
        with c4:
            expires = st.text_input("Expires",     value=e.get("expires",""))
            gdrive  = st.text_input("GDrive URL",  value=e.get("gdrive_url",""))
        notes = st.text_area("Notes", value=e.get("notes",""), height=70)
        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not name.strip():
                st.error("Lead name is required.")
                return None
            lid = e.get("lead_id") or _lead_id_from_name(name)
            return {
                "lead_id": lid, "name": name.strip(),
                "email": email, "phone": phone,
                "location": location, "city": city, "state": state,
                "services": services, "next_activity": next_activity,
                "poc": poc, "contact_name": contact_name,
                "gdrive_url": gdrive, "total_amount": total or None,
                "submittal_deadline": deadline, "expires": expires,
                "notes": notes,
            }
    return None


def render():
    init_crm_tables()
    section_header("Leads", "Sales pipeline — follow-ups, quotes, and conversions.")

    # ── Filter row ────────────────────────────────────────────────────────────
    cf1, cf2, cf3, cf4 = st.columns([4, 2, 2, 2])
    with cf1:
        search = st.text_input("🔍", placeholder="Name, email, contact…",
                               label_visibility="collapsed", key="crm_leads_search")
    with cf2:
        activities = get_lead_activities()
        act_opts = ["All"] + [a for a in activities if a]
        af = st.selectbox("Activity", act_opts, label_visibility="collapsed", key="crm_leads_act")
    with cf3:
        st_opts = ["All"] + [s for s in _STATES if s]
        stf = st.selectbox("State", st_opts, label_visibility="collapsed", key="crm_leads_state")
    with cf4:
        if st.button("➕ Add Lead", use_container_width=True):
            st.session_state["crm_lead_add"] = not st.session_state.get("crm_lead_add", False)

    # ── Add form ──────────────────────────────────────────────────────────────
    if st.session_state.get("crm_lead_add"):
        with st.container(border=True):
            st.markdown("**New Lead**")
            result = _lead_form("add")
            if result:
                upsert_lead(result)
                from app.services.sheets_sync import sync_crm_leads; sync_crm_leads()
                st.session_state["crm_lead_add"] = False
                st.toast("Lead added!", icon="🎯")
                st.rerun()

    # ── Fetch ─────────────────────────────────────────────────────────────────
    act_f = "" if af == "All" else af
    st_f  = "" if stf == "All" else stf
    leads = get_all_leads(next_activity=act_f, state=st_f, search=search)

    # ── Summary ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Leads", len(leads))
    states_count = {}
    for ld in leads:
        s = ld.get("state","")
        if s:
            states_count[s] = states_count.get(s, 0) + 1
    top_state = max(states_count, key=states_count.get) if states_count else "—"
    c2.metric("Top State", top_state)
    total_val = sum(ld.get("total_amount") or 0 for ld in leads)
    c3.metric("Pipeline Value", f"${total_val:,.0f}" if total_val else "—")
    st.markdown("---")

    if not leads:
        st.info("No leads found. Add one above or run CRM Import.", icon="🎯")
        return

    # ── Tabs by next_activity ─────────────────────────────────────────────────
    priority_acts = ["Follow Up","Add Info","Complete Work","Check-Email","MOS","Other"]
    present_acts  = list(dict.fromkeys(
        [ld.get("next_activity","") for ld in leads if ld.get("next_activity")]
    ))
    tab_acts  = [a for a in priority_acts if a != "Other"]
    tab_acts += [a for a in present_acts if a not in tab_acts]
    tab_acts  = ["All"] + tab_acts[:8]   # cap at 9 tabs

    tabs = st.tabs(tab_acts)

    for ti, tab in enumerate(tabs):
        tab_act = "" if ti == 0 else tab_acts[ti]
        tab_leads = [ld for ld in leads if tab_act == "" or ld.get("next_activity") == tab_act]

        with tab:
            if not tab_leads:
                st.caption("No leads in this category.")
                continue

            for lead in tab_leads:
                lid      = lead["lead_id"]
                edit_key = f"crm_lead_edit_{lid}"
                del_key  = f"crm_lead_del_{lid}"

                with st.container(border=True):
                    r1, r2, r3 = st.columns([5, 3, 4])
                    with r1:
                        amt_str = ""
                        if lead.get("total_amount"):
                            amt_str = (f' &nbsp; <span style="color:#1AB738;font-weight:600">'
                                       f'${lead["total_amount"]:,.0f}</span>')
                        st.markdown(
                            f'**{lead["name"]}** &nbsp; '
                            + _state_badge(lead.get("state",""))
                            + amt_str,
                            unsafe_allow_html=True,
                        )
                        if lead.get("services"):
                            st.caption(f"🔧 {lead['services']}")
                    with r2:
                        if lead.get("email"):
                            st.markdown(
                                f'📧 <a href="mailto:{lead["email"]}" style="color:#1AB738">'
                                f'{lead["email"]}</a>',
                                unsafe_allow_html=True,
                            )
                        if lead.get("contact_name"):
                            st.caption(f"👤 {lead['contact_name']}")
                    with r3:
                        st.markdown(
                            _activity_badge(lead.get("next_activity","")),
                            unsafe_allow_html=True,
                        )
                        if lead.get("submittal_deadline"):
                            st.caption(f"⏰ Due: {lead['submittal_deadline']}")
                        if lead.get("poc"):
                            st.caption(f"POC: {lead['poc']}")

                    # Details expander
                    if lead.get("location") or lead.get("gdrive_url") or lead.get("notes"):
                        with st.expander("Details", expanded=False):
                            if lead.get("location"):
                                st.markdown(f"📍 {lead['location']}")
                            if lead.get("gdrive_url"):
                                st.markdown(
                                    f'<a href="{lead["gdrive_url"]}" target="_blank" '
                                    f'style="color:#1AB738">📂 Google Drive</a>',
                                    unsafe_allow_html=True,
                                )
                            if lead.get("expires"):
                                st.markdown(f"Expires: {lead['expires']}")
                            if lead.get("notes"):
                                st.markdown(f"Notes: {lead['notes']}")

                    # Action buttons
                    ba1, ba2, ba3, ba4, _ = st.columns([1, 1, 1, 1, 3])
                    with ba1:
                        if st.button("✏️", key=f"ledit_{lid}", use_container_width=True,
                                     help="Edit lead"):
                            st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    with ba2:
                        if lead.get("email"):
                            st.markdown(
                                f'<a href="mailto:{lead["email"]}?subject=Sterling Stormwater — {lead["name"]}" '
                                f'style="display:inline-block;padding:5px 8px;background:rgba(255,255,255,0.05);'
                                f'border:1px solid #4b4e69;border-radius:6px;color:#9699a6;'
                                f'font-size:13px;text-decoration:none">📧</a>',
                                unsafe_allow_html=True,
                            )
                    with ba3:
                        if st.button("➡️ Job", key=f"lconvert_{lid}", use_container_width=True,
                                     help="Convert to Job"):
                            st.session_state["crm_new_job_prefill"] = {
                                "job_site": lead["name"],
                                "lead_id":  lid,
                                "service":  lead.get("services",""),
                            }
                            st.session_state["crm_job_add"] = True
                            set_page("crm_jobs")
                            st.rerun()
                    with ba4:
                        if st.button("🗑️", key=f"ldel_{lid}", use_container_width=True):
                            st.session_state[del_key] = True

                    # Edit form
                    if st.session_state.get(edit_key):
                        with st.container(border=True):
                            result = _lead_form(f"edit_{lid}", existing=lead)
                            if result:
                                upsert_lead(result)
                                from app.services.sheets_sync import sync_crm_leads; sync_crm_leads()
                                st.session_state[edit_key] = False
                                st.toast("Lead updated!", icon="✅")
                                st.rerun()

                    # Delete confirm
                    if st.session_state.get(del_key):
                        st.warning(f"Delete **{lead['name']}**?")
                        ld1, ld2, _ = st.columns([1, 1, 5])
                        with ld1:
                            if st.button("Yes", key=f"ldel_conf_{lid}", type="primary"):
                                delete_lead(lid)
                                st.session_state.pop(del_key, None)
                                st.rerun()
                        with ld2:
                            if st.button("No", key=f"ldel_cancel_{lid}"):
                                st.session_state.pop(del_key, None)
                                st.rerun()

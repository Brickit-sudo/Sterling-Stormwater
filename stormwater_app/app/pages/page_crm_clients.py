"""
app/pages/page_crm_clients.py
CRM — Clients / Contacts directory.
"""
import uuid
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.crm_db import (
    get_all_contacts, upsert_contact, delete_contact, init_crm_tables,
)

_STATUSES = ["Active","Inactive","Overdue","Email Sent","Email Received",""]
_STATES   = ["ME","MA","NH","VT","RI","CT","NY","NJ","PA","MD","Other",""]

_STATUS_STYLES = {
    "Active":         ("rgba(26,183,56,0.12)",  "#1AB738"),
    "Inactive":       ("rgba(150,153,166,0.15)","#9699a6"),
    "Overdue":        ("rgba(226,68,92,0.15)",  "#e2445c"),
    "Email Sent":     ("rgba(87,155,252,0.15)", "#579bfc"),
    "Email Received": ("rgba(255,203,0,0.15)",  "#ffcb00"),
}


def _status_badge(status: str) -> str:
    bg, color = _STATUS_STYLES.get(status, ("rgba(150,153,166,0.15)","#9699a6"))
    return (f'<span style="background:{bg};color:{color};padding:2px 8px;'
            f'border-radius:10px;font-size:11px;font-weight:600">{status or "—"}</span>')


def _contact_form(prefix: str, existing: dict | None = None) -> dict | None:
    e = existing or {}
    with st.form(key=f"contact_form_{prefix}"):
        c1, c2 = st.columns(2)
        with c1:
            first = st.text_input("First Name *", value=e.get("first_name",""))
            email = st.text_input("Email",        value=e.get("email",""))
            account = st.text_input("Account / Company", value=e.get("account",""))
            managed_by = st.text_input("Managed By", value=e.get("managed_by",""))
        with c2:
            last  = st.text_input("Last Name",    value=e.get("last_name",""))
            phone = st.text_input("Phone",        value=e.get("phone",""))
            state = st.selectbox("State", _STATES,
                                 index=_STATES.index(e.get("state","")) if e.get("state","") in _STATES else 0)
            status = st.selectbox("Status", _STATUSES,
                                  index=_STATUSES.index(e.get("active_status","Active")) if e.get("active_status","Active") in _STATUSES else 0)
        notes = st.text_area("Notes", value=e.get("notes",""), height=70)
        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not first.strip():
                st.error("First name is required.")
                return None
            cid = e.get("client_id") or f"SSC-{str(uuid.uuid4())[:8].upper()}"
            return {
                "client_id": cid, "first_name": first.strip(), "last_name": last.strip(),
                "email": email, "phone": phone, "account": account,
                "managed_by": managed_by, "active_status": status,
                "state": state, "notes": notes,
                "sites_managed": e.get("sites_managed",""),
            }
    return None


def render():
    init_crm_tables()
    section_header("Clients", "Contacts and account managers.")

    # ── Filter row ────────────────────────────────────────────────────────────
    c_s, c_f, c_add = st.columns([4, 2, 2])
    with c_s:
        search = st.text_input("🔍", placeholder="Name, email, company…",
                               label_visibility="collapsed", key="crm_contacts_search")
    with c_f:
        status_opts = ["All"] + [s for s in _STATUSES if s]
        sf = st.selectbox("Status", status_opts, label_visibility="collapsed",
                          key="crm_contacts_status")
    with c_add:
        if st.button("➕ Add Contact", use_container_width=True):
            st.session_state["crm_contact_add"] = not st.session_state.get("crm_contact_add", False)

    # ── Add form ──────────────────────────────────────────────────────────────
    if st.session_state.get("crm_contact_add"):
        with st.container(border=True):
            st.markdown("**New Contact**")
            result = _contact_form("add")
            if result:
                upsert_contact(result)
                st.session_state["crm_contact_add"] = False
                st.toast("Contact added!", icon="✅")
                st.rerun()

    # ── Fetch ─────────────────────────────────────────────────────────────────
    status_f = "" if sf == "All" else sf
    contacts = get_all_contacts(search=search, status=status_f)

    # ── Metrics ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contacts", len(contacts))
    active = sum(1 for c in contacts if c.get("active_status") == "Active")
    c2.metric("Active", active)
    overdue = sum(1 for c in contacts if c.get("active_status") == "Overdue")
    c3.metric("Overdue", overdue)
    st.markdown("---")

    if not contacts:
        st.info("No contacts found. Add one above or run CRM Import.", icon="👤")
        return

    for contact in contacts:
        cid      = contact["client_id"]
        full     = f"{contact.get('first_name','')} {contact.get('last_name','')}".strip() or cid
        edit_key = f"crm_contact_edit_{cid}"
        del_key  = f"crm_contact_del_{cid}"

        with st.container(border=True):
            r1, r2, r3 = st.columns([5, 3, 4])
            with r1:
                st.markdown(
                    f'**{full}** &nbsp; '
                    + _status_badge(contact.get("active_status",""))
                    + f' &nbsp; <span style="color:#4b4e69;font-size:11px">{cid}</span>',
                    unsafe_allow_html=True,
                )
                if contact.get("account"):
                    st.caption(f"🏢 {contact['account']}")
            with r2:
                if contact.get("email"):
                    st.markdown(
                        f'📧 <a href="mailto:{contact["email"]}" style="color:#1AB738">'
                        f'{contact["email"]}</a>',
                        unsafe_allow_html=True,
                    )
                if contact.get("phone"):
                    st.markdown(
                        f'📞 <a href="tel:{contact["phone"]}" style="color:#9699a6">'
                        f'{contact["phone"]}</a>',
                        unsafe_allow_html=True,
                    )
            with r3:
                if contact.get("managed_by"):
                    st.caption(f"👤 Mgr: {contact['managed_by']}")
                if contact.get("state"):
                    st.caption(f"📍 {contact['state']}")

            # Detail expander
            if contact.get("sites_managed") or contact.get("notes"):
                with st.expander("Details", expanded=False):
                    if contact.get("sites_managed"):
                        st.markdown("**Sites Managed:**")
                        for s in contact["sites_managed"].split(","):
                            if s.strip():
                                st.markdown(f"  • {s.strip()}")
                    if contact.get("notes"):
                        st.markdown(f"**Notes:** {contact['notes']}")

            # Actions
            ba1, ba2, ba3, _ = st.columns([1, 1, 1, 5])
            with ba1:
                if st.button("✏️ Edit", key=f"cedit_{cid}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
            with ba2:
                if contact.get("email"):
                    subj = "Sterling Stormwater — Follow Up"
                    st.markdown(
                        f'<a href="mailto:{contact["email"]}?subject={subj}" '
                        f'style="display:inline-block;padding:5px 10px;background:rgba(255,255,255,0.05);'
                        f'border:1px solid #4b4e69;border-radius:6px;color:#9699a6;'
                        f'font-size:13px;text-decoration:none">📧 Email</a>',
                        unsafe_allow_html=True,
                    )
            with ba3:
                if st.button("🗑️", key=f"cdel_{cid}", use_container_width=True):
                    st.session_state[del_key] = True

            # Edit form
            if st.session_state.get(edit_key):
                with st.container(border=True):
                    result = _contact_form(f"edit_{cid}", existing=contact)
                    if result:
                        upsert_contact(result)
                        st.session_state[edit_key] = False
                        st.toast("Contact updated!", icon="✅")
                        st.rerun()

            # Delete confirm
            if st.session_state.get(del_key):
                st.warning(f"Delete **{full}**?")
                dc1, dc2, _ = st.columns([1, 1, 5])
                with dc1:
                    if st.button("Yes, delete", key=f"cdel_conf_{cid}", type="primary"):
                        delete_contact(cid)
                        st.session_state.pop(del_key, None)
                        st.rerun()
                with dc2:
                    if st.button("Cancel", key=f"cdel_cancel_{cid}"):
                        st.session_state.pop(del_key, None)
                        st.rerun()

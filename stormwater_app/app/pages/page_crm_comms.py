"""
app/pages/page_crm_comms.py
Client communications log — email, calls, notes with entity links.
"""
import uuid
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.crm_db import (
    get_communications, upsert_communication, delete_communication,
    init_crm_tables,
)

_TYPES = ["email", "call", "note", "file", "meeting"]
_DIRECTIONS = ["outbound", "inbound"]
_ENTITY_TYPES = ["site", "contact", "lead", "job"]

_TYPE_ICON = {
    "email":   "📧",
    "call":    "📞",
    "note":    "📝",
    "file":    "📎",
    "meeting": "🤝",
}
_TYPE_COLOR = {
    "email":   ("#579bfc20", "#579bfc"),
    "call":    ("#1AB73820", "#1AB738"),
    "note":    ("#ffcb0020", "#ffcb00"),
    "file":    ("#a25ddc20", "#a25ddc"),
    "meeting": ("#e2445c20", "#e2445c"),
}
_DIR_LABEL = {"outbound": "↗ Outbound", "inbound": "↙ Inbound"}


def _type_badge(t: str) -> str:
    bg, col = _TYPE_COLOR.get(t, ("#30324e20", "#9699a6"))
    icon = _TYPE_ICON.get(t, "📋")
    return (f'<span style="background:{bg};color:{col};padding:2px 8px;'
            f'border-radius:8px;font-size:11px;font-weight:600">'
            f'{icon} {t.title()}</span>')


def _dir_badge(d: str) -> str:
    color = "#1AB738" if d == "outbound" else "#579bfc"
    return (f'<span style="color:{color};font-size:11px;font-weight:500">'
            f'{_DIR_LABEL.get(d, d)}</span>')


def _comm_form(prefix: str, existing: dict | None = None) -> dict | None:
    e = existing or {}
    with st.form(key=f"comm_form_{prefix}"):
        c1, c2 = st.columns(2)
        with c1:
            entity_type = st.selectbox(
                "Link to",
                _ENTITY_TYPES,
                index=_ENTITY_TYPES.index(e.get("entity_type", "site")) if e.get("entity_type") in _ENTITY_TYPES else 0,
            )
            entity_id = st.text_input("Entity ID (site/contact/job/lead ID)",
                                      value=e.get("entity_id", ""))
            entity_name = st.text_input("Entity Name (display)", value=e.get("entity_name", ""))
        with c2:
            comm_type = st.selectbox(
                "Type",
                _TYPES,
                index=_TYPES.index(e.get("type", "email")) if e.get("type") in _TYPES else 0,
            )
            direction = st.selectbox(
                "Direction",
                _DIRECTIONS,
                index=_DIRECTIONS.index(e.get("direction", "outbound")) if e.get("direction") in _DIRECTIONS else 0,
            )
            created_by = st.text_input("Created By", value=e.get("created_by", "B. Rolfe"))
        subject = st.text_input("Subject / Summary", value=e.get("subject", ""))
        body = st.text_area("Body / Notes", value=e.get("body", ""), height=120)
        attachment_url = st.text_input("Attachment URL (optional)",
                                       value=e.get("attachment_url", ""))
        submitted = st.form_submit_button("💾 Save", type="primary")
        if submitted:
            if not subject.strip():
                st.error("Subject is required.")
                return None
            return {
                "comm_id":        e.get("comm_id") or f"CRM-{str(uuid.uuid4())[:8].upper()}",
                "entity_type":    entity_type,
                "entity_id":      entity_id.strip() or "general",
                "entity_name":    entity_name.strip(),
                "type":           comm_type,
                "direction":      direction,
                "subject":        subject.strip(),
                "body":           body.strip(),
                "attachment_url": attachment_url.strip() or None,
                "created_by":     created_by.strip() or "B. Rolfe",
                "created_at":     e.get("created_at"),
            }
    return None


def render():
    init_crm_tables()
    section_header("Communications", "Email logs, call notes, and file records by client/site.")

    # ── Filter row ────────────────────────────────────────────────────────────
    cf1, cf2, cf3, cf4 = st.columns([4, 2, 2, 2])
    with cf1:
        search = st.text_input("🔍", placeholder="Subject, name, ID…",
                               label_visibility="collapsed", key="crm_comm_search")
    with cf2:
        et_opts = ["All"] + _ENTITY_TYPES
        et_f = st.selectbox("Entity", et_opts, label_visibility="collapsed",
                            key="crm_comm_entity")
    with cf3:
        tp_opts = ["All"] + _TYPES
        tp_f = st.selectbox("Type", tp_opts, label_visibility="collapsed",
                            key="crm_comm_type")
    with cf4:
        if st.button("➕ Log Communication", use_container_width=True):
            st.session_state["crm_comm_add"] = not st.session_state.get("crm_comm_add", False)

    # ── Add form ──────────────────────────────────────────────────────────────
    if st.session_state.get("crm_comm_add"):
        with st.container(border=True):
            st.markdown("**New Communication Log**")
            result = _comm_form("add")
            if result:
                upsert_communication(result)
                st.session_state["crm_comm_add"] = False
                st.toast("Communication logged!", icon="💬")
                st.rerun()

    # ── Fetch + filter ────────────────────────────────────────────────────────
    et_filter = "" if et_f == "All" else et_f
    tp_filter = "" if tp_f == "All" else tp_f
    comms = get_communications(entity_type=et_filter, comm_type=tp_filter,
                               search=search, limit=200)

    # ── Summary ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Logged", len(comms))
    emails = sum(1 for c in comms if c.get("type") == "email")
    c2.metric("Emails", emails)
    calls = sum(1 for c in comms if c.get("type") == "call")
    c3.metric("Calls", calls)
    notes = sum(1 for c in comms if c.get("type") == "note")
    c4.metric("Notes", notes)
    st.markdown("---")

    if not comms:
        st.info("No communications logged yet. Click '➕ Log Communication' to get started.", icon="💬")
        return

    # ── Comm list ─────────────────────────────────────────────────────────────
    for comm in comms:
        cid      = comm["comm_id"]
        edit_key = f"crm_comm_edit_{cid}"
        del_key  = f"crm_comm_del_{cid}"

        with st.container(border=True):
            r1, r2, r3 = st.columns([5, 3, 3])
            with r1:
                st.markdown(
                    f'**{comm.get("subject","(no subject)")}** &nbsp;'
                    + _type_badge(comm.get("type", "note")),
                    unsafe_allow_html=True,
                )
                if comm.get("entity_name"):
                    st.caption(
                        f"{comm['entity_type'].title()}: {comm['entity_name']} "
                        f"· {comm.get('entity_id', '')}"
                    )
            with r2:
                st.markdown(
                    _dir_badge(comm.get("direction", "outbound")),
                    unsafe_allow_html=True,
                )
                if comm.get("created_by"):
                    st.caption(f"👤 {comm['created_by']}")
            with r3:
                if comm.get("created_at"):
                    ts = comm["created_at"][:16].replace("T", " ")
                    st.caption(f"🕐 {ts}")

            if comm.get("body"):
                preview = comm["body"][:200] + ("…" if len(comm["body"]) > 200 else "")
                with st.expander("View Details", expanded=False):
                    st.markdown(comm["body"])
                    if comm.get("attachment_url"):
                        st.markdown(
                            f'📎 <a href="{comm["attachment_url"]}" target="_blank" '
                            f'style="color:#1AB738">Attachment</a>',
                            unsafe_allow_html=True,
                        )
            elif comm.get("attachment_url"):
                st.markdown(
                    f'📎 <a href="{comm["attachment_url"]}" target="_blank" '
                    f'style="color:#1AB738">Attachment</a>',
                    unsafe_allow_html=True,
                )

            ba1, ba2, _ = st.columns([1, 1, 6])
            with ba1:
                if st.button("✏️ Edit", key=f"cedit_{cid}", use_container_width=True):
                    st.session_state[edit_key] = not st.session_state.get(edit_key, False)
            with ba2:
                if st.button("🗑️", key=f"cdel_{cid}", use_container_width=True):
                    st.session_state[del_key] = True

            if st.session_state.get(edit_key):
                with st.container(border=True):
                    result = _comm_form(f"edit_{cid}", existing=comm)
                    if result:
                        upsert_communication(result)
                        st.session_state[edit_key] = False
                        st.toast("Updated!", icon="✅")
                        st.rerun()

            if st.session_state.get(del_key):
                st.warning("Delete this communication log?")
                dd1, dd2, _ = st.columns([1, 1, 5])
                with dd1:
                    if st.button("Yes", key=f"cdel_conf_{cid}", type="primary"):
                        delete_communication(cid)
                        st.session_state.pop(del_key, None)
                        st.rerun()
                with dd2:
                    if st.button("No", key=f"cdel_cancel_{cid}"):
                        st.session_state.pop(del_key, None)
                        st.rerun()

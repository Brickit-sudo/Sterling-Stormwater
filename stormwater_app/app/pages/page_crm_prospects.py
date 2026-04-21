"""
app/pages/page_crm_prospects.py
Prospects Pipeline — 372 Excel-imported companies to reach out to.
"""
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.api_client import get_all_prospects, update_prospect

_STATUS_FLOW  = ["New", "Contacted", "Qualified", "Converted", "Dead"]
_PRIORITY_COLOR = {"High": "#e2445c", "Medium": "#ffcb00", "Low": "#579bfc"}
_STATUS_COLOR   = {
    "New":       "#579bfc",
    "Contacted": "#ffcb00",
    "Qualified": "#a25ddc",
    "Converted": "#1AB738",
    "Dead":      "#9699a6",
}


def _priority_badge(p: str) -> str:
    color = _PRIORITY_COLOR.get(p, "#9699a6")
    return (f'<span style="background:{color}20;color:{color};padding:1px 7px;'
            f'border-radius:6px;font-size:11px;font-weight:600">{p or "—"}</span>')


def _status_badge(s: str) -> str:
    color = _STATUS_COLOR.get(s, "#9699a6")
    return (f'<span style="background:{color}20;color:{color};padding:2px 8px;'
            f'border-radius:8px;font-size:11px;font-weight:600">{s}</span>')


def render():
    section_header("Prospects", "372 target accounts — track outreach and conversions.")

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns([4, 2, 2, 2])
    with f1:
        search = st.text_input("🔍", placeholder="Company, city, BMP type…",
                               label_visibility="collapsed", key="pros_search")
    with f2:
        status_f = st.selectbox("Status", ["All"] + _STATUS_FLOW,
                                label_visibility="collapsed", key="pros_status")
    with f3:
        priority_f = st.selectbox("Priority", ["All", "High", "Medium", "Low"],
                                  label_visibility="collapsed", key="pros_priority")
    with f4:
        state_f = st.selectbox("State", ["All", "ME", "VA", "MA", "NH", "NY", "Other"],
                               label_visibility="collapsed", key="pros_state")

    s_filter = "" if status_f == "All" else status_f
    p_filter = "" if priority_f == "All" else priority_f
    prospects = get_all_prospects(status=s_filter, priority=p_filter, search=search)

    if state_f != "All":
        prospects = [p for p in prospects if p.get("state") == state_f]

    # ── Summary ───────────────────────────────────────────────────────────────
    total = len(prospects)
    high  = sum(1 for p in prospects if p.get("lead_priority") == "High")
    conv  = sum(1 for p in prospects if p.get("status") == "Converted")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total",     total)
    c2.metric("High Priority", high)
    c3.metric("Converted", conv)
    st.markdown("---")

    if not prospects:
        st.info("No prospects match the current filters.", icon="🎯")
        return

    # ── Tabs by status ────────────────────────────────────────────────────────
    tabs = st.tabs(["All"] + _STATUS_FLOW)

    for ti, tab in enumerate(tabs):
        tab_status = "" if ti == 0 else _STATUS_FLOW[ti - 1]
        tab_pros = [p for p in prospects if not tab_status or p.get("status") == tab_status]

        with tab:
            if not tab_pros:
                st.caption("No prospects in this stage.")
                continue

            for pros in tab_pros:
                pid = str(pros["lead_id"])
                edit_key = f"pros_edit_{pid}"

                with st.container(border=True):
                    r1, r2, r3 = st.columns([5, 4, 3])
                    with r1:
                        st.markdown(
                            f'**{pros.get("company_name", "—")}** &nbsp; '
                            + _priority_badge(pros.get("lead_priority", "")) + " &nbsp; "
                            + _status_badge(pros.get("status", "")),
                            unsafe_allow_html=True,
                        )
                        if pros.get("site_description"):
                            st.caption(f'🏢 {pros["site_description"]}')
                        addr_parts = [pros.get("address"), pros.get("city"), pros.get("state")]
                        addr = ", ".join(p for p in addr_parts if p)
                        if addr:
                            st.caption(f"📍 {addr}")
                    with r2:
                        if pros.get("compliance_type"):
                            st.caption(f"📋 {pros['compliance_type']}")
                        if pros.get("property_type"):
                            st.caption(f"🏗️ {pros['property_type']}")
                        if pros.get("contact_email"):
                            st.markdown(
                                f'📧 <a href="mailto:{pros["contact_email"]}" style="color:#1AB738;font-size:12px">'
                                f'{pros["contact_email"]}</a>',
                                unsafe_allow_html=True,
                            )
                    with r3:
                        if pros.get("contact_phone"):
                            st.caption(f"📞 {pros['contact_phone']}")
                        if pros.get("decision_maker_type"):
                            st.caption(f"👤 {pros['decision_maker_type']}")
                        if pros.get("observed_bmps"):
                            bmps = pros["observed_bmps"]
                            st.caption(f"🌊 {bmps[:60]}{'…' if len(bmps) > 60 else ''}")

                    # Notes expander
                    if pros.get("notes_for_outreach"):
                        with st.expander("Outreach Notes", expanded=False):
                            st.markdown(pros["notes_for_outreach"])
                            if pros.get("permit_indicator"):
                                st.caption(f"Permit: {pros['permit_indicator']}")

                    # Quick status change
                    act_cols = st.columns([2, 2, 4])
                    with act_cols[0]:
                        new_status = st.selectbox(
                            "Move to", [""] + _STATUS_FLOW,
                            index=0, key=f"pros_move_{pid}",
                            label_visibility="collapsed",
                        )
                        if new_status and new_status != pros.get("status"):
                            result = update_prospect(pid, {"status": new_status})
                            if result:
                                st.toast(f"{pros['company_name']} → {new_status}", icon="✅")
                                st.rerun()
                    with act_cols[1]:
                        if pros.get("contact_email"):
                            st.markdown(
                                f'<a href="mailto:{pros["contact_email"]}?subject=Sterling Stormwater Stormwater Services" '
                                f'style="display:inline-block;padding:5px 10px;background:rgba(255,255,255,0.05);'
                                f'border:1px solid #4b4e69;border-radius:6px;color:#9699a6;'
                                f'font-size:12px;text-decoration:none">📧 Email</a>',
                                unsafe_allow_html=True,
                            )

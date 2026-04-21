"""
app/pages/page_crm_quotes.py
Quote Builder — create proposals using the service catalog. Pick site → add services → done.
"""
import streamlit as st
from datetime import date, timedelta
from app.components.ui_helpers import section_header
from app.services.api_client import (
    get_all_quotes, create_quote, update_quote,
    get_all_service_items, get_all_sites,
)

_STATUS_OPTS  = ["Draft", "Sent", "Accepted", "Rejected", "Expired"]
_STATUS_COLOR = {
    "Draft":    "#9699a6",
    "Sent":     "#579bfc",
    "Accepted": "#1AB738",
    "Rejected": "#e2445c",
    "Expired":  "#ffcb00",
}


def _status_badge(s: str) -> str:
    color = _STATUS_COLOR.get(s, "#9699a6")
    return (f'<span style="background:{color}20;color:{color};padding:2px 8px;'
            f'border-radius:8px;font-size:11px;font-weight:600">{s}</span>')


def _quote_builder_form(preselect_site_id: str = "") -> dict | None:
    sites    = get_all_sites()
    services = get_all_service_items()

    if not sites:
        st.warning("No sites found. Make sure the backend is running and you have sites in the database.")
        return None

    site_options = {f'{s.get("name","?")} — {s.get("client_name","?")}': s for s in sites}
    labels = list(site_options.keys())
    default_idx = 0
    if preselect_site_id:
        for i, s in enumerate(sites):
            if str(s.get("site_id", "")) == str(preselect_site_id):
                default_idx = i
                break

    with st.form("quote_builder_form"):
        st.markdown("**1. Site**")
        selected_label = st.selectbox("Site *", labels, index=default_idx)
        site = site_options[selected_label]

        st.markdown("**2. Quote Details**")
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            quote_number  = st.text_input("Quote Number", value=f"Q-{date.today().strftime('%Y%m%d')}")
            quote_date    = st.date_input("Quote Date", value=date.today())
        with qc2:
            expiry_date   = st.date_input("Expiry Date", value=date.today() + timedelta(days=30))
            contract_num  = st.text_input("Contract #", value="")
        with qc3:
            status        = st.selectbox("Status", _STATUS_OPTS)
            notes         = st.text_area("Notes", height=68)

        st.markdown("**3. Line Items**")
        st.caption("Select from catalog, or type a custom description. Leave price blank to fill in later.")

        # Up to 8 line items
        line_items = []
        for i in range(8):
            cols = st.columns([4, 1, 2, 2])
            svc_labels = ["— custom —"] + [s["name"] for s in services]
            with cols[0]:
                selected_svc = st.selectbox(f"Service {i+1}", svc_labels,
                                            key=f"qb_svc_{i}", label_visibility="collapsed")
            with cols[1]:
                qty = st.number_input("Qty", min_value=0.0, step=1.0, key=f"qb_qty_{i}",
                                      label_visibility="collapsed", value=1.0)
            with cols[2]:
                # Auto-fill price from catalog
                default_price = 0.0
                svc_obj = None
                if selected_svc != "— custom —":
                    svc_obj = next((s for s in services if s["name"] == selected_svc), None)
                    default_price = float(svc_obj.get("default_unit_price") or 0) if svc_obj else 0.0
                price = st.number_input("Unit $", min_value=0.0, step=25.0, key=f"qb_price_{i}",
                                        label_visibility="collapsed", value=default_price)
            with cols[3]:
                custom_desc = st.text_input("Custom desc", key=f"qb_desc_{i}",
                                            label_visibility="collapsed",
                                            placeholder="(optional override)")

            if selected_svc != "— custom —" or custom_desc.strip():
                desc = custom_desc.strip() if custom_desc.strip() else selected_svc
                amount = round(qty * price, 2) if qty and price else None
                li = {
                    "description": desc,
                    "quantity": qty if qty else None,
                    "unit_price": price if price else None,
                    "amount": amount,
                    "sort_order": i,
                }
                if svc_obj:
                    li["service_item_id"] = str(svc_obj["service_id"])
                line_items.append(li)

        if line_items:
            total = sum(li.get("amount") or 0 for li in line_items)
            st.markdown(
                f'<div style="text-align:right;font-size:16px;font-weight:700;color:#1AB738;'
                f'padding:8px 0">Total: ${total:,.2f}</div>',
                unsafe_allow_html=True,
            )

        submitted = st.form_submit_button("💾 Create Quote", type="primary")
        if submitted:
            if not line_items:
                st.error("Add at least one line item.")
                return None
            return {
                "site_id":       str(site["site_id"]),
                "client_id":     str(site["client_id"]),
                "quote_number":  quote_number or None,
                "quote_date":    str(quote_date),
                "expiry_date":   str(expiry_date),
                "status":        status,
                "contract_number": contract_num or None,
                "notes":         notes or None,
                "line_items":    line_items,
            }
    return None


def render():
    section_header("Quote Builder", "Build proposals from your service catalog — no re-typing.")

    # ── New quote toggle ──────────────────────────────────────────────────────
    preselect_site_id = st.session_state.pop("new_quote_site_id", "")
    if preselect_site_id:
        st.session_state["qb_open"] = True

    col_hdr, col_btn = st.columns([6, 2])
    with col_btn:
        if st.button("➕ New Quote", use_container_width=True, type="primary"):
            st.session_state["qb_open"] = not st.session_state.get("qb_open", False)

    if st.session_state.get("qb_open"):
        with st.container(border=True):
            result = _quote_builder_form(preselect_site_id=preselect_site_id)
            if result:
                created = create_quote(result)
                if created:
                    st.session_state["qb_open"] = False
                    st.toast(f'Quote {result.get("quote_number", "")} created!', icon="✅")
                    st.rerun()
                else:
                    st.error("Failed to create quote — check that the backend is running.")
        st.markdown("---")

    # ── Filter ────────────────────────────────────────────────────────────────
    sf1, sf2 = st.columns([4, 2])
    with sf2:
        qstatus_f = st.selectbox("Status", ["All"] + _STATUS_OPTS,
                                 label_visibility="collapsed", key="q_status_f")

    s_filter = "" if qstatus_f == "All" else qstatus_f
    quotes = get_all_quotes(status=s_filter)

    if not quotes:
        st.info("No quotes yet. Create one above.", icon="📝")
        return

    # ── Summary ───────────────────────────────────────────────────────────────
    total_val = sum((q.get("total_amount") or 0) for q in quotes)
    accepted  = sum(1 for q in quotes if q.get("status") == "Accepted")
    q1, q2, q3 = st.columns(3)
    q1.metric("Total Quotes", len(quotes))
    q2.metric("Accepted",     accepted)
    q3.metric("Value",        f"${total_val:,.0f}")
    st.markdown("---")

    # ── Quote cards ───────────────────────────────────────────────────────────
    tabs = st.tabs(["All"] + _STATUS_OPTS)
    for ti, tab in enumerate(tabs):
        tab_status = "" if ti == 0 else _STATUS_OPTS[ti - 1]
        tab_quotes = [q for q in quotes if not tab_status or q.get("status") == tab_status]

        with tab:
            if not tab_quotes:
                st.caption("No quotes in this status.")
                continue

            for q in tab_quotes:
                qid = str(q["quote_id"])
                with st.container(border=True):
                    rc1, rc2, rc3 = st.columns([4, 3, 3])
                    with rc1:
                        st.markdown(
                            f'**{q.get("quote_number") or qid[:8]}** &nbsp; '
                            + _status_badge(q.get("status", "")),
                            unsafe_allow_html=True,
                        )
                        st.caption(f'📍 Site: {q.get("site_id", "—")}')
                    with rc2:
                        st.caption(f'📅 {q.get("quote_date") or "—"}')
                        if q.get("expiry_date"):
                            st.caption(f'⏰ Expires: {q["expiry_date"]}')
                    with rc3:
                        total = q.get("total_amount")
                        st.markdown(
                            f'<span style="color:#1AB738;font-size:16px;font-weight:700">'
                            f'{"$"+f"{float(total):,.2f}" if total else "—"}</span>',
                            unsafe_allow_html=True,
                        )

                    # Line items preview
                    if q.get("line_items"):
                        with st.expander(f"{len(q['line_items'])} line items", expanded=False):
                            for li in q["line_items"]:
                                amt = li.get("amount")
                                amt_str = f"  —  ${float(amt):,.2f}" if amt else ""
                                st.caption(f'• {li.get("description", "—")}{amt_str}')

                    # Quick status update
                    sc1, _ = st.columns([2, 6])
                    with sc1:
                        new_s = st.selectbox("Status", [""] + _STATUS_OPTS,
                                             index=0, key=f"q_upd_{qid}",
                                             label_visibility="collapsed")
                        if new_s and new_s != q.get("status"):
                            result = update_quote(qid, {"status": new_s})
                            if result:
                                st.toast(f"Quote → {new_s}", icon="✅")
                                st.rerun()

"""
app/pages/page_crm_invoices.py
Invoice Tracker — view, filter, and update status on all invoices.
"""
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.api_client import get_all_invoices, get_invoice_summary, update_invoice

_STATUS_OPTS = ["Not Paid", "Paid", "Partial", "Void"]
_STATUS_COLOR = {
    "Not Paid": "#e2445c",
    "Partial":  "#ffcb00",
    "Paid":     "#1AB738",
    "Void":     "#9699a6",
}


def _badge(status: str) -> str:
    color = _STATUS_COLOR.get(status, "#9699a6")
    return (
        f'<span style="background:{color}20;color:{color};padding:2px 8px;'
        f'border-radius:8px;font-size:11px;font-weight:600">{status}</span>'
    )


def render():
    section_header("Invoices", "Track billing, payments, and outstanding balances.")

    # ── Summary bar ───────────────────────────────────────────────────────────
    summary = get_invoice_summary()
    s1, s2, s3 = st.columns(3)
    s1.metric("Total Invoices",  summary.get("total_count", 0))
    s2.metric("Total Billed",    f"${summary.get('total_billed', 0):,.0f}")
    s3.metric("Outstanding",     f"${summary.get('total_outstanding', 0):,.0f}")
    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([4, 2, 2])
    with f1:
        search = st.text_input("🔍", placeholder="Invoice #, site, or client…",
                               label_visibility="collapsed", key="inv_search")
    with f2:
        status_f = st.selectbox("Status", ["All"] + _STATUS_OPTS,
                                label_visibility="collapsed", key="inv_status")
    with f3:
        sort_f = st.selectbox("Sort", ["Date ↓", "Date ↑", "Amount ↓", "Amount ↑"],
                              label_visibility="collapsed", key="inv_sort")

    s_filter = "" if status_f == "All" else status_f
    invoices = get_all_invoices(status=s_filter, search=search)

    # Sort
    rev = "↓" in sort_f
    key_fn = (lambda i: i.get("invoice_date") or "") if "Date" in sort_f else (lambda i: i.get("invoice_total") or 0)
    invoices = sorted(invoices, key=key_fn, reverse=rev)

    if not invoices:
        st.info("No invoices found.", icon="🧾")
        return

    # ── Status tabs ───────────────────────────────────────────────────────────
    tab_labels = ["All"] + _STATUS_OPTS
    tabs = st.tabs(tab_labels)

    for ti, tab in enumerate(tabs):
        tab_status = "" if ti == 0 else tab_labels[ti]
        tab_invs = [i for i in invoices if not tab_status or i.get("status") == tab_status]

        with tab:
            if not tab_invs:
                st.caption("No invoices in this status.")
                continue

            tab_total = sum(i.get("invoice_total") or 0 for i in tab_invs)
            tab_outstanding = sum(i.get("balance_due") or 0 for i in tab_invs)
            tc1, tc2, tc3 = st.columns(3)
            tc1.metric("Count", len(tab_invs))
            tc2.metric("Billed", f"${tab_total:,.0f}")
            tc3.metric("Outstanding", f"${tab_outstanding:,.0f}")
            st.markdown("")

            for inv in tab_invs:
                inv_id = str(inv["invoice_id"])
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
                    with c1:
                        st.markdown(
                            f'**{inv.get("invoice_number", "—")}** &nbsp; '
                            + _badge(inv.get("status", "")),
                            unsafe_allow_html=True,
                        )
                        st.caption(f'📍 {inv.get("site_name") or inv.get("site_id", "—")}')
                        if inv.get("client_name"):
                            st.caption(f'👤 {inv["client_name"]}')
                    with c2:
                        date_str = inv.get("invoice_date") or "—"
                        st.caption(f"📅 {date_str}")
                        if inv.get("contract_number"):
                            st.caption(f"📄 Contract: {inv['contract_number']}")
                        if inv.get("po_number"):
                            st.caption(f"PO: {inv['po_number']}")
                    with c3:
                        total = inv.get("invoice_total")
                        st.markdown(
                            f'<div style="font-size:16px;font-weight:700;color:#d5d8df">'
                            f'{"$"+f"{total:,.2f}" if total is not None else "—"}</div>',
                            unsafe_allow_html=True,
                        )
                    with c4:
                        balance = inv.get("balance_due")
                        color = "#e2445c" if balance else "#1AB738"
                        st.markdown(
                            f'<div style="font-size:14px;font-weight:600;color:{color}">'
                            f'{"Due: $"+f"{balance:,.2f}" if balance else "✓ Paid"}</div>',
                            unsafe_allow_html=True,
                        )

                    # Quick status update
                    col_status, col_spacer = st.columns([2, 6])
                    with col_status:
                        new_status = st.selectbox(
                            "Status", [""] + _STATUS_OPTS,
                            index=0, key=f"inv_upd_{inv_id}",
                            label_visibility="collapsed",
                        )
                        if new_status and new_status != inv.get("status"):
                            balance_due = 0.0 if new_status == "Paid" else inv.get("balance_due")
                            result = update_invoice(inv_id, {"status": new_status, "balance_due": balance_due})
                            if result:
                                st.toast(f"Invoice {inv.get('invoice_number')} → {new_status}", icon="✅")
                                st.rerun()
                            else:
                                st.error("Update failed — is the backend running?")

"""
app/pages/page_crm_jobs.py
CRM — Jobs Dashboard. Track work orders by status, owner, revenue.
"""
import uuid
import streamlit as st
import pandas as pd
from app.components.ui_helpers import section_header
from app.services.crm_db import (
    get_all_jobs, upsert_job, delete_job,
    get_job_statuses, get_job_owners, get_job_months, init_crm_tables,
)

_STATUS_OPTS = ["Need to Schedule","Scheduled","Report in Progress","Ready for Review","Complete"]
_OWNERS      = ["Bryce Rolfe","Scott Rolfe","Scott Rolfe, Crew 1","Other"]
_MONTHS      = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]

_STATUS_COLOR = {
    "Need to Schedule":   "#e2445c",
    "Scheduled":          "#ffcb00",
    "Report in Progress": "#579bfc",
    "Ready for Review":   "#a25ddc",
    "Complete":           "#1AB738",
}


def _badge(status: str) -> str:
    color = _STATUS_COLOR.get(status, "#9699a6")
    return (f'<span style="background:{color}20;color:{color};padding:2px 7px;'
            f'border-radius:8px;font-size:11px;font-weight:600">{status}</span>')


def _add_job_form(prefill: dict | None = None) -> dict | None:
    p = prefill or {}
    with st.form("crm_add_job_form"):
        c1, c2 = st.columns(2)
        with c1:
            job_site  = st.text_input("Job Site *",  value=p.get("job_site",""))
            location  = st.text_input("Location",    value=p.get("location",""))
            service   = st.text_input("Service Type",value=p.get("service",""))
            owner     = st.selectbox("Owner", _OWNERS,
                                     index=_OWNERS.index(p.get("owner","Bryce Rolfe")) if p.get("owner","Bryce Rolfe") in _OWNERS else 0)
        with c2:
            job_status    = st.selectbox("Status", _STATUS_OPTS,
                                         index=_STATUS_OPTS.index(p.get("job_status","Scheduled")) if p.get("job_status","Scheduled") in _STATUS_OPTS else 1)
            sched_month   = st.selectbox("Scheduled Month", [""]+_MONTHS,
                                         index=0)
            sched_date    = st.text_input("Scheduled Date (YYYY-MM-DD)", value=p.get("scheduled_date",""))
            quoted_amount = st.number_input("Quoted ($)", min_value=0.0, step=50.0,
                                            value=float(p.get("quoted_amount") or 0))
        c3, c4 = st.columns(2)
        with c3:
            actual_amount = st.number_input("Actual ($)", min_value=0.0, step=50.0,
                                            value=float(p.get("actual_amount") or 0))
            site_id   = st.text_input("Site ID (SSW-XXXX)", value=p.get("site_id",""))
        with c4:
            client_id = st.text_input("Client ID (SSC-XXXX)", value=p.get("client_id",""))
            lead_id   = st.text_input("Lead ID (SWL-XXXX)",   value=p.get("lead_id",""))
        notes = st.text_area("Scope / Notes", value=p.get("notes",""), height=70)
        submitted = st.form_submit_button("💾 Add Job", type="primary")
        if submitted:
            if not job_site.strip():
                st.error("Job site is required.")
                return None
            return {
                "job_id": f"SSO-{str(uuid.uuid4())[:8].upper()}",
                "job_site": job_site.strip(), "location": location,
                "job_status": job_status, "service": service,
                "scope": notes, "scheduled_month": sched_month,
                "scheduled_date": sched_date, "owner": owner,
                "quoted_amount": quoted_amount or None,
                "actual_amount": actual_amount or None,
                "site_id": site_id or None, "client_id": client_id or None,
                "lead_id": lead_id or None, "gdrive_url": None,
                "notes": notes,
            }
    return None


def render():
    init_crm_tables()
    section_header("Jobs", "Work orders — track status, revenue, and scheduling.")

    # ── Filter bar ────────────────────────────────────────────────────────────
    cf1, cf2, cf3, cf4, cf5 = st.columns([3, 2, 2, 2, 2])
    with cf1:
        search = st.text_input("🔍", placeholder="Site or service…",
                               label_visibility="collapsed", key="crm_jobs_search")
    with cf2:
        status_list = ["All"] + get_job_statuses() or ["All"] + _STATUS_OPTS
        sf = st.selectbox("Status", status_list, label_visibility="collapsed", key="crm_jobs_status")
    with cf3:
        owner_list = ["All"] + get_job_owners() or ["All"] + _OWNERS
        of = st.selectbox("Owner",  owner_list,  label_visibility="collapsed", key="crm_jobs_owner")
    with cf4:
        month_list = ["All"] + get_job_months() or ["All"] + _MONTHS
        mf = st.selectbox("Month",  month_list,  label_visibility="collapsed", key="crm_jobs_month")
    with cf5:
        if st.button("➕ Add Job", use_container_width=True):
            st.session_state["crm_job_add"] = not st.session_state.get("crm_job_add", False)

    # ── Add form ──────────────────────────────────────────────────────────────
    if st.session_state.get("crm_job_add"):
        prefill = st.session_state.pop("crm_new_job_prefill", None)
        with st.container(border=True):
            st.markdown("**New Job**")
            result = _add_job_form(prefill)
            if result:
                upsert_job(result)
                st.session_state["crm_job_add"] = False
                st.toast("Job added!", icon="✅")
                st.rerun()

    # ── Fetch jobs ────────────────────────────────────────────────────────────
    status_f = "" if sf == "All" else sf
    owner_f  = "" if of == "All" else of
    month_f  = "" if mf == "All" else mf
    jobs = get_all_jobs(status=status_f, owner=owner_f, month=month_f, search=search)

    # ── Summary cards ─────────────────────────────────────────────────────────
    total_quoted = sum(j.get("quoted_amount") or 0 for j in jobs)
    total_actual = sum(j.get("actual_amount") or 0 for j in jobs)
    open_jobs    = sum(1 for j in jobs if j.get("job_status") != "Complete")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Jobs",    len(jobs))
    c2.metric("Open",          open_jobs)
    c3.metric("Quoted",        f"${total_quoted:,.0f}")
    c4.metric("Actual",        f"${total_actual:,.0f}")
    st.markdown("---")

    if not jobs:
        st.info("No jobs match the current filters.", icon="🔧")
        return

    # ── Tabs by status ────────────────────────────────────────────────────────
    tab_labels = ["All"] + _STATUS_OPTS
    tabs = st.tabs(tab_labels)

    for ti, tab in enumerate(tabs):
        tab_status = "" if ti == 0 else tab_labels[ti]
        tab_jobs = [j for j in jobs if tab_status == "" or j.get("job_status") == tab_status]

        with tab:
            if not tab_jobs:
                st.caption("No jobs in this status.")
                continue

            for job in tab_jobs:
                jid     = job["job_id"]
                del_key = f"crm_job_del_{jid}"

                with st.container(border=True):
                    r1, r2, r3 = st.columns([5, 3, 4])
                    with r1:
                        st.markdown(
                            f'**{job.get("job_site","—")}** &nbsp; '
                            + _badge(job.get("job_status",""))
                            + f' &nbsp; <span style="color:#4b4e69;font-size:11px">{jid}</span>',
                            unsafe_allow_html=True,
                        )
                        if job.get("service"):
                            st.caption(f"🔧 {job['service']}")
                    with r2:
                        if job.get("owner"):
                            st.caption(f"👤 {job['owner']}")
                        if job.get("scheduled_date") or job.get("scheduled_month"):
                            when = job.get("scheduled_date") or job.get("scheduled_month","")
                            st.caption(f"📅 {when}")
                    with r3:
                        q = job.get("quoted_amount")
                        a = job.get("actual_amount")
                        if q:
                            st.caption(f"💰 Quoted: ${q:,.0f}")
                        if a:
                            st.caption(f"✅ Actual: ${a:,.0f}")

                    # Quick status update
                    new_status = st.selectbox(
                        "Update Status", [""] + _STATUS_OPTS,
                        index=0, key=f"status_upd_{jid}",
                        label_visibility="collapsed",
                    )
                    if new_status and new_status != job.get("job_status"):
                        upd = dict(job)
                        upd["job_status"] = new_status
                        upsert_job(upd)
                        st.toast(f"Status → {new_status}", icon="✅")
                        st.rerun()

                    # Delete
                    bd1, _ = st.columns([1, 7])
                    with bd1:
                        if st.button("🗑️ Delete", key=f"jdel_{jid}", use_container_width=True):
                            st.session_state[del_key] = True
                    if st.session_state.get(del_key):
                        st.warning(f"Delete **{job.get('job_site')}** ({jid})?")
                        jd1, jd2, _ = st.columns([1, 1, 5])
                        with jd1:
                            if st.button("Yes", key=f"jdel_conf_{jid}", type="primary"):
                                delete_job(jid)
                                st.session_state.pop(del_key, None)
                                st.rerun()
                        with jd2:
                            if st.button("No", key=f"jdel_cancel_{jid}"):
                                st.session_state.pop(del_key, None)
                                st.rerun()

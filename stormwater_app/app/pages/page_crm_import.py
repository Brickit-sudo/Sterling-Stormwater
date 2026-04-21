"""
app/pages/page_crm_import.py
CRM Import — upload Monday.com Excel exports or auto-detect from Downloads folder.
"""
import tempfile
import glob as _glob
from pathlib import Path
import streamlit as st
from app.components.ui_helpers import section_header
from app.services.crm_import import import_excel
from app.services.crm_db import get_crm_stats, init_crm_tables

_IMPORT_KINDS = [
    ("sites",    "📍 Site Information",  "SSW-XXXX", "Site_Information_*.xlsx"),
    ("contacts", "👤 Contacts",          "SSC-XXXX", "Contacts_*.xlsx"),
    ("jobs",     "🔧 Jobs / Orders",     "SSO-XXXX", "Order_*.xlsx"),
    ("leads",    "🎯 Leads",             "SWL-XXXX", "Leads_*.xlsx"),
]

_DOWNLOADS_ROOTS = [
    Path.home() / "Downloads",
    Path("C:/Users") / Path.home().name / "Downloads",
]


def _find_downloads(pattern: str) -> list[Path]:
    found = []
    for root in _DOWNLOADS_ROOTS:
        if root.exists():
            found.extend(root.glob(pattern))
    return sorted(set(found))


def render():
    init_crm_tables()
    section_header("CRM Import", "Import Monday.com exports to populate the database.")

    # ── DB Stats ──────────────────────────────────────────────────────────────
    try:
        stats = get_crm_stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sites",    stats["sites"])
        c2.metric("Contacts", stats["contacts"])
        c3.metric("Jobs",     stats["jobs"])
        c4.metric("Leads",    stats["leads"])
    except Exception:
        st.caption("Stats unavailable — tables may be empty.")

    st.markdown("---")
    st.info(
        "**Safe to re-run.** Import uses upsert logic — rows are inserted or updated "
        "by their Monday ID (SSW/SSC/SSO/SWL). Local notes you've added are preserved.",
        icon="ℹ️",
    )

    # ── Quick Import from Downloads ───────────────────────────────────────────
    auto_found = []
    for kind, label, id_fmt, pattern in _IMPORT_KINDS:
        for fp in _find_downloads(pattern):
            auto_found.append((kind, label, fp))

    if auto_found:
        st.markdown("### ⚡ Quick Import — Files Detected in Downloads")
        for kind, label, fp in auto_found:
            col_f, col_b = st.columns([6, 2])
            with col_f:
                st.caption(f"{label} · `{fp.name}`")
            with col_b:
                if st.button(f"Import", key=f"qi_{fp.name}_{kind}", use_container_width=True):
                    with st.spinner(f"Importing {fp.name}…"):
                        res = import_excel(kind, str(fp))
                    if res.get("errors", 0) == 0:
                        st.success(res["message"])
                    else:
                        st.warning(res["message"])
                    st.rerun()
        st.markdown("---")

    # ── Manual Upload ─────────────────────────────────────────────────────────
    st.markdown("### 📤 Upload New Files")
    uploaded: dict[str, object] = {}

    cols = st.columns(2)
    for i, (kind, label, id_fmt, _pattern) in enumerate(_IMPORT_KINDS):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(f"IDs: `{id_fmt}`")
                f = st.file_uploader(
                    f"Upload {label} .xlsx",
                    type=["xlsx"],
                    key=f"import_{kind}",
                    label_visibility="collapsed",
                )
                if f:
                    uploaded[kind] = f

    if uploaded:
        if st.button("🚀 Import All Uploaded Files", type="primary", use_container_width=True):
            all_ok = True
            for kind, f_obj in uploaded.items():
                suffix = ".xlsx"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(f_obj.read())
                    tmp_path = tmp.name
                with st.spinner(f"Importing {f_obj.name}…"):
                    res = import_excel(kind, tmp_path)
                Path(tmp_path).unlink(missing_ok=True)
                if res.get("errors", 0) == 0:
                    st.success(f"✅ **{f_obj.name}** — {res['message']}")
                else:
                    st.warning(f"⚠️ **{f_obj.name}** — {res['message']}")
                    all_ok = False
            if all_ok:
                st.balloons()
            st.rerun()

    # ── Email integration info ────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📧 Email Integration Options", expanded=False):
        st.markdown("""
**How email works in this CRM:**

**Mailto links (active now)**
Click the 📧 button on any contact or lead — it opens your default email client
(Gmail, Outlook, Apple Mail) with the recipient pre-filled and a Sterling subject line.
No configuration needed.

**Send emails directly from the app (optional setup)**

To enable in-app sending via Gmail:
1. Go to your Google Account → Security → App Passwords
2. Generate a new app password for "Mail"
3. Enter your settings below

To enable via Outlook / O365:
1. Use SMTP settings: `smtp.office365.com`, port 587
2. Your email and password (or app password if MFA is on)
""")
        with st.form("smtp_config_form"):
            c1, c2 = st.columns(2)
            with c1:
                smtp_host  = st.text_input("SMTP Server",
                                           value=st.session_state.get("smtp_host","smtp.gmail.com"),
                                           placeholder="smtp.gmail.com or smtp.office365.com")
                smtp_port  = st.number_input("Port", value=int(st.session_state.get("smtp_port",587)),
                                             min_value=25, max_value=65535)
            with c2:
                smtp_user  = st.text_input("Email Address",
                                           value=st.session_state.get("smtp_user",""))
                smtp_pass  = st.text_input("App Password", type="password",
                                           value=st.session_state.get("smtp_pass",""))
            if st.form_submit_button("💾 Save SMTP Settings"):
                st.session_state.update({
                    "smtp_host": smtp_host, "smtp_port": smtp_port,
                    "smtp_user": smtp_user, "smtp_pass": smtp_pass,
                })
                st.success("SMTP settings saved for this session.")

        # Test send
        if st.session_state.get("smtp_user") and st.session_state.get("smtp_pass"):
            test_to = st.text_input("Test recipient email", key="smtp_test_to")
            if st.button("📤 Send Test Email"):
                try:
                    import smtplib, ssl
                    context = ssl.create_default_context()
                    with smtplib.SMTP(st.session_state["smtp_host"],
                                      int(st.session_state["smtp_port"])) as srv:
                        srv.ehlo()
                        srv.starttls(context=context)
                        srv.login(st.session_state["smtp_user"],
                                  st.session_state["smtp_pass"])
                        msg = (f"Subject: Sterling Stormwater — Test Email\n\n"
                               f"Your email integration is working!")
                        srv.sendmail(st.session_state["smtp_user"], test_to, msg)
                    st.success(f"Test email sent to {test_to}!")
                except Exception as e:
                    st.error(f"Send failed: {e}")

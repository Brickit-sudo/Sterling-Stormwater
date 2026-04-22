"""
app/pages/page_google_settings.py
Google Sheets + Drive integration setup & sync controls.
"""

import json
import streamlit as st
from app.services.google_service import (
    is_configured, save_credentials, load_config, save_config,
    test_connection, service_email, sync_to_sheet,
)


def _section(title: str, icon: str = "") -> None:
    st.markdown(
        f'<div style="font-size:13px;font-weight:600;color:#9699a6;'
        f'text-transform:uppercase;letter-spacing:.08em;margin:20px 0 10px">'
        f'{icon} {title}</div>',
        unsafe_allow_html=True,
    )


def _status_chip(ok: bool, msg: str) -> None:
    color = "#00c875" if ok else "#e2445c"
    icon  = "✓" if ok else "✗"
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{color}18;border:1px solid {color}40;'
        f'border-radius:6px;padding:6px 12px;font-size:13px;color:{color}">'
        f'<span>{icon}</span><span>{msg}</span></div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(
        '<h2 style="font-size:1.4rem;font-weight:700;margin:0 0 4px">🔗 Google Integration</h2>'
        '<p style="color:#9699a6;font-size:13px;margin:0 0 20px">'
        'Connect Google Drive for report storage and Google Sheets for CRM sync.</p>',
        unsafe_allow_html=True,
    )

    cfg = load_config()

    # ── Step 1: Credentials ───────────────────────────────────────────────────
    _section("Step 1 — Service Account Credentials", "🔑")

    configured = is_configured()
    if configured:
        _status_chip(True, f"Credentials loaded · {service_email()}")
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        ok, msg = test_connection()
        _status_chip(ok, msg)

        with st.expander("Replace credentials"):
            _upload_credentials()
    else:
        st.info(
            "Upload your Google service account JSON key to get started. "
            "No credentials are stored in the cloud — the file stays local.",
            icon="ℹ️",
        )
        _upload_credentials()

    if not configured:
        st.markdown(
            '<div style="background:#1c2240;border:1px solid rgba(255,255,255,0.08);'
            'border-radius:8px;padding:16px;margin-top:16px;font-size:13px;color:#9699a6">'
            '<b style="color:#d5d8df">How to create a service account:</b><br><br>'
            '1. Go to <b>console.cloud.google.com</b><br>'
            '2. Create a project → Enable <b>Google Drive API</b> + <b>Google Sheets API</b><br>'
            '3. IAM &amp; Admin → Service Accounts → Create Service Account<br>'
            '4. Keys tab → Add Key → JSON → Download<br>'
            '5. Upload the downloaded JSON file above<br><br>'
            '<b style="color:#d5d8df">Then share your Drive folder / Sheets with:</b><br>'
            '<code style="color:#1AB738">your-bot@your-project.iam.gserviceaccount.com</code>'
            '</div>',
            unsafe_allow_html=True,
        )
        _render_change_password()
        return

    # ── Step 2: Google Drive ──────────────────────────────────────────────────
    _section("Step 2 — Google Drive", "📁")

    col1, col2 = st.columns(2)
    reports_folder = col1.text_input(
        "Reports folder ID",
        value=cfg.get("drive_reports_folder", ""),
        placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        help="The ID from the Drive folder URL: drive.google.com/drive/folders/THIS_PART",
        key="g_drive_reports",
    )
    archive_folder = col2.text_input(
        "Archive folder ID",
        value=cfg.get("drive_archive_folder", ""),
        placeholder="Optional — separate folder for archived reports",
        key="g_drive_archive",
    )

    if st.button("Save Drive Config", key="save_drive"):
        cfg["drive_reports_folder"] = reports_folder
        cfg["drive_archive_folder"] = archive_folder
        save_config(cfg)
        st.toast("Drive config saved", icon="✅")

    if reports_folder:
        st.caption(f"Reports will upload to: `{reports_folder}`")

    # ── Step 3: Google Sheets ─────────────────────────────────────────────────
    _section("Step 3 — Google Sheets", "📊")

    sheet_url = st.text_input(
        "CRM Spreadsheet URL",
        value=cfg.get("sheets_crm_url", ""),
        placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
        help="Share this sheet with your service account email (Editor access).",
        key="g_sheet_url",
    )

    if st.button("Save Sheets Config", key="save_sheets"):
        cfg["sheets_crm_url"] = sheet_url
        save_config(cfg)
        st.toast("Sheets config saved", icon="✅")

    # ── Step 4: Calendar & Email config ──────────────────────────────────────────
    _section("Step 4 — Calendar & Email (Optional)", "📅")
    st.info(
        "Gmail send and Calendar sync require **Domain-Wide Delegation** enabled for your "
        "service account in Google Workspace Admin. Personal Gmail accounts are not supported.",
        icon="ℹ️",
    )
    col_cal, col_sender = st.columns(2)
    calendar_id = col_cal.text_input(
        "Google Calendar ID",
        value=cfg.get("google_calendar_id", ""),
        placeholder="primary or calendar@group.calendar.google.com",
        key="g_calendar_id",
    )
    sender_email = col_sender.text_input(
        "Sender email (Gmail)",
        value=cfg.get("gmail_sender", ""),
        placeholder="you@yourdomain.com",
        key="g_sender_email",
    )
    notebooklm_folder = st.text_input(
        "NotebookLM Drive Folder ID",
        value=cfg.get("notebooklm_folder_id", ""),
        placeholder="Drive folder ID — add this folder as a NotebookLM source",
        key="g_notebooklm_folder",
    )
    if st.button("Save Calendar / Email Config", key="save_cal_email"):
        cfg["google_calendar_id"] = calendar_id
        cfg["gmail_sender"] = sender_email
        cfg["notebooklm_folder_id"] = notebooklm_folder
        save_config(cfg)
        st.toast("Calendar & email config saved", icon="✅")

    # ── Step 5: Sync CRM to Sheets ────────────────────────────────────────────
    if cfg.get("sheets_crm_url"):
        _section("Step 5 — Sync CRM Data to Google Sheets", "🔄")
        st.caption(f"Destination: {cfg['sheets_crm_url']}")

        c1, c2, c3, c4 = st.columns(4)
        sync_sites  = c1.button("Sync Sites",    use_container_width=True, key="sync_sites")
        sync_jobs   = c2.button("Sync Jobs",     use_container_width=True, key="sync_jobs")
        sync_leads  = c3.button("Sync Leads",    use_container_width=True, key="sync_leads")
        sync_all    = c4.button("Sync All ▶",   use_container_width=True,
                                type="primary",  key="sync_all")

        if sync_sites or sync_all:
            _do_sync("Sites",   "crm_sites",   cfg["sheets_crm_url"])
        if sync_jobs or sync_all:
            _do_sync("Jobs",    "crm_jobs",    cfg["sheets_crm_url"])
        if sync_leads or sync_all:
            _do_sync("Leads",   "crm_leads",   cfg["sheets_crm_url"])
        if sync_all:
            _do_sync("Contacts", "crm_contacts", cfg["sheets_crm_url"])

    # ── Connected status summary ──────────────────────────────────────────────
    _section("Integration Status", "📡")
    col_a, col_b = st.columns(2)
    col_a.metric("Drive configured",  "Yes" if cfg.get("drive_reports_folder") else "No")
    col_b.metric("Sheets configured", "Yes" if cfg.get("sheets_crm_url")       else "No")

    _render_change_password()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upload_credentials() -> None:
    uploaded = st.file_uploader(
        "Service account JSON key",
        type=["json"],
        key="goog_creds_upload",
        help="Downloaded from Google Cloud Console → IAM → Service Accounts → Keys",
    )
    if uploaded:
        try:
            creds = json.loads(uploaded.read())
            required = {"type", "project_id", "private_key", "client_email"}
            if not required.issubset(creds.keys()):
                st.error("Invalid service account JSON — missing required fields.")
                return
            if creds.get("type") != "service_account":
                st.error('JSON "type" must be "service_account".')
                return
            save_credentials(creds)
            # Clear cache so new creds are picked up
            st.cache_resource.clear()
            st.success(f"Credentials saved for: **{creds['client_email']}**")
            st.rerun()
        except Exception as e:
            st.error(f"Could not parse JSON: {e}")


def _render_change_password() -> None:
    _section("Account — Change Password", "🔒")
    with st.form("change_pw_form", border=False):
        cur_pw  = st.text_input("Current password",      type="password", placeholder="••••••••")
        new_pw1 = st.text_input("New password",          type="password", placeholder="••••••••",
                                help="Minimum 8 characters")
        new_pw2 = st.text_input("Confirm new password",  type="password", placeholder="••••••••")
        save_pw = st.form_submit_button("Update Password")

    if save_pw:
        from app.services.db import local_login, set_local_password
        user  = st.session_state.get("current_user", {})
        email = user.get("email", "")
        if not email:
            st.error("No user session found.")
        elif not cur_pw or not new_pw1:
            st.error("All fields are required.")
        elif new_pw1 != new_pw2:
            st.error("New passwords don't match.")
        elif len(new_pw1) < 8:
            st.error("Password must be at least 8 characters.")
        elif not local_login(email, cur_pw):
            st.error("Current password is incorrect.")
        else:
            set_local_password(email, new_pw1)
            st.success("Password updated successfully.")


def _do_sync(label: str, table: str, sheet_url: str) -> None:
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent.parent.parent / "stormwater.db"
    with st.spinner(f"Syncing {label}..."):
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
            conn.close()
            n = sync_to_sheet(sheet_url, label, rows)
            st.toast(f"{label}: {n} rows synced ✓", icon="✅")
        except Exception as e:
            st.error(f"{label} sync failed: {e}")

"""
app/pages/page_sync.py
Drive → Sheets Sync: catalog all Drive files and extract data from reports.

Changes from previous version:
- _step_header() updated to use new text contrast tokens
- Step connector refined
- No structural changes — stepper logic was already correct
"""

import re
import streamlit as st
from datetime import datetime, timezone
from app.services.google_service import (
    load_config, save_config, is_configured,
    crawl_drive_folder, download_pdf_text, sync_to_sheet,
)
from app.services.llm_service import classify_document, extract_document_fields


def render() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:24px">'
        '<div style="width:32px;height:32px;border-radius:8px;'
        'background:rgba(26,183,56,0.14);border:1px solid rgba(26,183,56,0.35);'
        'display:flex;align-items:center;justify-content:center;font-size:15px;color:#1AB738">↻</div>'
        '<div>'
        '<div style="font-size:16px;font-weight:700;color:#f0f2f6;letter-spacing:-0.01em">'
        'Drive → Sheets Sync</div>'
        '<div style="font-size:12px;color:#7c7f96">'
        'Catalog your Drive files and extract structured data into Google Sheets</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if not is_configured():
        st.warning("Google integration not configured. Go to Settings → Google Integration first.")
        return

    cfg = load_config()
    root_folder_id = cfg.get("sync_root_folder_id", "")
    sheet_url = cfg.get("sync_sheet_url", "")
    ready = bool(root_folder_id and sheet_url)
    cataloged = bool(cfg.get("catalog_file_count"))

    # ── Step 1: Configuration ─────────────────────────────────────────────────
    _step_header(1, "Configuration", "Connect your Drive folder and destination sheet",
                 "done" if ready else "active")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        new_folder = col1.text_input(
            "Root Drive Folder ID",
            value=root_folder_id,
            placeholder="Folder ID or full Drive URL",
            help="From the Drive URL: drive.google.com/drive/folders/THIS_PART",
            key="sync_root_folder",
        )
        new_sheet = col2.text_input(
            "Destination Google Sheet URL",
            value=sheet_url,
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="sync_sheet_url_input",
        )
        if st.button("Save Configuration", key="save_sync_cfg"):
            cfg["sync_root_folder_id"] = _extract_folder_id(new_folder)
            cfg["sync_sheet_url"] = new_sheet
            save_config(cfg)
            st.toast("Sync config saved", icon="✅")
            st.rerun()

    if not ready:
        _step_connector(done=False)
        _step_header(2, "File Catalog", "Crawl Drive and build a complete file inventory", "pending")
        _step_connector(done=False)
        _step_header(3, "Data Extraction", "AI-powered field extraction from report PDFs", "pending")
        return

    # ── Step 2: File Catalog ──────────────────────────────────────────────────
    _step_connector(done=True)
    _step_header(2, "File Catalog", "Crawl Drive and build a complete file inventory",
                 "done" if cataloged else "active")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Last Catalog",  cfg.get("last_catalog",  "Never"))
        c2.metric("Files Found",   cfg.get("catalog_file_count", "—"))
        c3.metric("Sites Found",   cfg.get("catalog_site_count", "—"))
        st.caption(
            "Crawls all site subfolders and writes a complete file inventory to the "
            "'File Index' and 'Site Registry' sheet tabs. No AI, no cost."
        )

        if st.button("▶  Run Catalog", type="primary", key="run_catalog"):
            with st.spinner("Crawling Drive folders…"):
                try:
                    files = crawl_drive_folder(root_folder_id)
                except Exception as e:
                    st.error(f"Drive crawl failed: {e}")
                    return

            if not files:
                st.warning("No files found. Check your folder ID and service account access.")
                return

            sites: dict = {}
            for f in files:
                sn = f["site_name"]
                if sn not in sites:
                    sites[sn] = {
                        "site_name":        sn,
                        "site_folder_id":   f["site_folder_id"],
                        "drive_folder_url": f"https://drive.google.com/drive/folders/{f['site_folder_id']}",
                        "file_count":       0,
                    }
                sites[sn]["file_count"] += 1

            progress = st.progress(0, text="Writing to Google Sheets…")
            try:
                sync_to_sheet(sheet_url, "File Index", files)
                progress.progress(0.5, text="Writing Site Registry…")
                sync_to_sheet(sheet_url, "Site Registry", list(sites.values()))
                progress.progress(1.0, text="Done")
            except Exception as e:
                st.error(f"Sheets write failed: {e}")
                return

            cfg["last_catalog"]       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            cfg["catalog_file_count"] = str(len(files))
            cfg["catalog_site_count"] = str(len(sites))
            save_config(cfg)
            st.success(
                f"Cataloged **{len(files)} files** across **{len(sites)} sites** → written to Google Sheets."
            )
            st.rerun()

    if not cataloged:
        _step_connector(done=False)
        _step_header(3, "Data Extraction", "AI-powered field extraction from report PDFs", "pending")
        return

    # ── Step 3: Data Extraction ───────────────────────────────────────────────
    _step_connector(done=True)
    _step_header(3, "Data Extraction", "AI-powered field extraction from report PDFs", "active")
    with st.container(border=True):
        st.caption(
            "Select which document types to extract. Images and unrecognized files are skipped automatically."
        )
        col_a, col_b, col_c, col_d = st.columns(4)
        do_inspection  = col_a.checkbox("Inspection Reports",  value=True,  key="do_inspection")
        do_maintenance = col_b.checkbox("Maintenance Reports", value=True,  key="do_maintenance")
        do_invoices    = col_c.checkbox("Invoices",            value=False, key="do_invoices")
        do_proposals   = col_d.checkbox("Proposals",           value=False, key="do_proposals")

        selected_types = []
        if do_inspection:  selected_types.append("inspection_report")
        if do_maintenance: selected_types.append("maintenance_report")
        if do_invoices:    selected_types.append("invoice")
        if do_proposals:   selected_types.append("proposal")

        if selected_types:
            file_count     = int(cfg.get("catalog_file_count", 0) or 0)
            estimated_docs = max(1, int(file_count * 0.6))
            est_cost       = estimated_docs * 0.002
            st.info(
                f"Estimated: ~{estimated_docs} PDFs to process · **~${est_cost:.2f}** (Claude Haiku pricing)",
                icon="💰",
            )
        else:
            st.warning("Select at least one document type.")

        if st.button("▶  Run Extraction", type="primary", key="run_extract",
                     disabled=not selected_types):
            with st.spinner("Re-crawling Drive for PDFs…"):
                try:
                    all_files = crawl_drive_folder(root_folder_id)
                except Exception as e:
                    st.error(f"Drive crawl failed: {e}")
                    return

            pdfs = [f for f in all_files if f["file_ext"] == "pdf"]
            st.write(f"Found **{len(pdfs)} PDFs** to process.")

            inspection_rows, maintenance_rows, invoice_rows, proposal_rows = [], [], [], []
            errors: list[str] = []
            progress = st.progress(0, text="Starting extraction…")

            for i, f in enumerate(pdfs):
                progress.progress(
                    (i + 1) / len(pdfs),
                    text=f"Processing {i + 1}/{len(pdfs)}: {f['file_name'][:50]}",
                )
                try:
                    text = download_pdf_text(f["file_id"])
                    if not text.strip():
                        continue

                    doc_type = classify_document(text)
                    if doc_type not in selected_types:
                        continue

                    fields = extract_document_fields(text, doc_type)
                    if not fields:
                        continue

                    row = {
                        "site_name":    f["site_name"],
                        "file_name":    f["file_name"],
                        "drive_url":    f["url"],
                        "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        **{k: (str(v) if not isinstance(v, str) else v)
                           for k, v in fields.items()},
                    }

                    if doc_type == "inspection_report":    inspection_rows.append(row)
                    elif doc_type == "maintenance_report": maintenance_rows.append(row)
                    elif doc_type == "invoice":            invoice_rows.append(row)
                    elif doc_type == "proposal":           proposal_rows.append(row)

                except Exception as e:
                    errors.append(f"{f['file_name']}: {e}")

            progress.progress(1.0, text="Writing to Sheets…")
            try:
                if inspection_rows:  sync_to_sheet(sheet_url, "Inspection Log",  inspection_rows)
                if maintenance_rows: sync_to_sheet(sheet_url, "Service History", maintenance_rows)
                if invoice_rows:     sync_to_sheet(sheet_url, "Invoices",        invoice_rows)
                if proposal_rows:    sync_to_sheet(sheet_url, "Proposals",       proposal_rows)
            except Exception as e:
                st.error(f"Sheets write failed: {e}")
                return

            cfg["last_extract"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            save_config(cfg)

            total = (len(inspection_rows) + len(maintenance_rows)
                     + len(invoice_rows) + len(proposal_rows))
            st.success(
                f"Extracted **{total} documents**: "
                f"{len(inspection_rows)} inspections, {len(maintenance_rows)} maintenance, "
                f"{len(invoice_rows)} invoices, {len(proposal_rows)} proposals."
            )
            if errors:
                with st.expander(f"{len(errors)} errors"):
                    for e in errors:
                        st.text(e)
            st.rerun()


# ── Stepper helpers ───────────────────────────────────────────────────────────

def _step_header(num: int, title: str, subtitle: str, status: str) -> None:
    dot_bg     = {"done": "#1AB738",              "active": "rgba(26,183,56,0.14)", "pending": "#30324e"}[status]
    dot_border = {"done": "#1AB738",              "active": "#1AB738",              "pending": "#4b4e69"}[status]
    dot_color  = {"done": "#04140A",              "active": "#1AB738",              "pending": "#6e6f8f"}[status]
    dot_icon   = "✓" if status == "done" else str(num)
    label_color = "#1AB738" if status in ("done", "active") else "#6e6f8f"
    step_label  = {"done": "Completed", "active": "Current Step", "pending": "Pending"}[status]
    glow        = "box-shadow:0 0 0 4px rgba(26,183,56,0.18);" if status == "active" else ""

    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:12px;margin:16px 0 8px">'
        f'<div style="width:28px;height:28px;border-radius:50%;background:{dot_bg};'
        f'border:2px solid {dot_border};color:{dot_color};flex-shrink:0;margin-top:2px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:12px;font-weight:700;{glow}">{dot_icon}</div>'
        f'<div>'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.10em;color:{label_color};margin-bottom:2px;'
        f'font-family:\'JetBrains Mono\',monospace">'
        f'Step {num} · {step_label}</div>'
        f'<div style="font-size:15px;font-weight:700;color:#f0f2f6;letter-spacing:-0.01em">'
        f'{title}</div>'
        f'<div style="font-size:12px;color:#7c7f96;margin-top:2px">{subtitle}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _step_connector(done: bool) -> None:
    color = "#1AB738" if done else "#4b4e69"
    st.markdown(
        f'<div style="width:2px;height:20px;background:{color};'
        f'margin:4px 0 4px 13px;border-radius:1px;'
        f'transition:background 300ms"></div>',
        unsafe_allow_html=True,
    )


def _extract_folder_id(value: str) -> str:
    """Accept a bare folder ID or a full Drive URL — return just the ID."""
    value = value.strip()
    if "drive.google.com" in value:
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", value)
        if match:
            return match.group(1)
    return value

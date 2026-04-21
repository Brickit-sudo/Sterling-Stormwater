"""
app/pages/page_setup.py
Screen 1: Import previous report (prominent, at top) then report metadata form.
"""

import streamlit as st
from datetime import date
from app.session import get_project, set_page
from app.constants import REPORT_TYPES
from app.components.ui_helpers import section_header, nav_buttons
from app.services.importer import extract_text_from_file, extract_fields
from app.services.db import get_all_clients, get_sites_for_client, get_report_count_for_site


def _apply_auto_fill(proj, extracted_fields: dict) -> list[str]:
    """
    Copy extracted values into meta where the field is currently empty.
    Returns a list of human-readable field names that were filled.
    """
    meta = proj.meta
    filled = []

    mapping = [
        ("report_type",     "report_type",    "Report Type"),
        ("site_name",       "site_name",       "Site Name"),
        ("site_address",    "site_address",    "Site Location / Address"),
        ("prepared_by",     "prepared_by",     "Performed By"),
        ("inspection_date", "inspection_date", "Inspection / Service Date"),
    ]

    for ext_key, meta_key, label in mapping:
        value = extracted_fields.get(ext_key, "")
        if value and not getattr(meta, meta_key):
            setattr(meta, meta_key, value)
            filled.append(label)

    return filled


def _render_site_picker(meta) -> None:
    """
    Collapsible section: pick an existing client + site from the DB.
    When selected, pre-fills client_name, site_name, and site_address.
    """
    clients = get_all_clients()
    if not clients:
        return  # No history yet — skip the picker silently

    with st.expander("📂 Open Existing Client / Site", expanded=False):
        client_names = [c["name"] for c in clients]
        sel_client = st.selectbox(
            "Client", ["— select —"] + client_names, key="picker_client"
        )
        if sel_client == "— select —":
            return

        client_id = next(c["client_id"] for c in clients if c["name"] == sel_client)
        sites     = get_sites_for_client(client_id)

        if not sites:
            st.caption("No sites found for this client.")
            return

        site_names = [s["name"] for s in sites]
        sel_site   = st.selectbox("Site", ["— select —"] + site_names, key="picker_site")
        if sel_site == "— select —":
            return

        site      = next(s for s in sites if s["name"] == sel_site)
        n_reports = get_report_count_for_site(sel_client, sel_site)

        st.markdown(
            f"**{sel_site}** · {n_reports} prior report(s) on file  "
            f"· Address: {site.get('address') or '—'}"
        )

        if st.button("Load Client / Site Info", key="picker_apply", type="primary"):
            meta.client_name  = sel_client
            meta.site_name    = sel_site
            meta.site_address = site.get("address", "")
            st.success(f"Loaded: {sel_client} — {sel_site}")
            st.rerun()


def render():
    section_header(
        "Report Setup",
        "Import a previous report to auto-fill fields, then review and complete setup."
    )

    proj = get_project()
    meta = proj.meta

    # ── 0. EXISTING CLIENT / SITE PICKER ─────────────────────────────────────
    _render_site_picker(meta)

    st.markdown("---")

    # ── 1. IMPORT PREVIOUS REPORT (prominent, not collapsed) ──────────────────
    st.markdown("### Import Previous Report")
    st.caption(
        "Upload a PDF or DOCX from a prior inspection or maintenance report. "
        "Fields will be auto-filled from the extracted content — review and edit below."
    )

    uploaded = st.file_uploader(
        "Upload Previous Report (PDF or DOCX)",
        type=["pdf", "docx"],
        help="File is read locally — nothing is sent to a server.",
        key="import_uploader",
    )

    if uploaded is not None:
        with st.spinner("Extracting and analyzing report..."):
            raw_result = extract_text_from_file(uploaded)

        if raw_result.get("error"):
            st.error(f"Could not extract text: {raw_result['error']}")
        else:
            raw_text = raw_result.get("raw_text", "")
            extracted = extract_fields(raw_text)
            st.session_state.import_extracted = extracted

            # Store raw sections for write-ups page
            proj.imported_text = raw_result.get("sections", {})
            if not proj.imported_text and raw_text:
                proj.imported_text = {"Full Document": raw_text}

            # Apply auto-fill only on first extraction (not if already applied)
            if not st.session_state.get("import_applied", False):
                filled = _apply_auto_fill(proj, extracted)
                st.session_state.import_applied = True
                st.session_state.import_filled_fields = filled
            else:
                filled = st.session_state.get("import_filled_fields", [])

            # Auto-fill banner
            n_filled = len(filled)
            if n_filled > 0:
                st.success(
                    f"Auto-filled {n_filled} field(s) from previous report. "
                    "Review and edit below.",
                    icon="✅",
                )
                st.markdown("**Fields filled:**")
                for f in filled:
                    st.markdown(f"- {f}")
            else:
                st.info(
                    "Text extracted successfully. No new fields were auto-filled "
                    "(fields may already have values).",
                    icon="ℹ️",
                )

            if extracted.get("system_types"):
                st.markdown(
                    "**System types detected:** "
                    + ", ".join(extracted["system_types"])
                )

            if extracted.get("raw_summary"):
                with st.expander("View extracted summary text", expanded=False):
                    st.text_area(
                        "Extracted summary",
                        value=extracted["raw_summary"],
                        height=150,
                        key="import_summary_preview",
                        label_visibility="collapsed",
                    )

    elif st.session_state.get("import_applied"):
        # Previously imported — show status and allow clearing
        filled = st.session_state.get("import_filled_fields", [])
        st.success(
            f"Previous report imported — {len(filled)} field(s) auto-filled. "
            f"{len(proj.imported_text)} section(s) available on Write-Ups page.",
            icon="📂",
        )
        if st.button("Clear Import", key="clear_import"):
            st.session_state.import_extracted = {}
            st.session_state.import_applied = False
            st.session_state.import_filled_fields = []
            proj.imported_text = {}
            st.rerun()

    st.markdown("---")

    # ── 2. REPORT TYPE ────────────────────────────────────────────────────────
    rt_index = REPORT_TYPES.index(meta.report_type) if meta.report_type in REPORT_TYPES else 0
    meta.report_type = st.selectbox(
        "Report Type",
        REPORT_TYPES,
        index=rt_index,
        help="Controls which sections appear in the generated report.",
    )

    is_inspection = meta.report_type in ("Inspection", "Inspection and Maintenance")
    is_maintenance = meta.report_type in ("Maintenance", "Inspection and Maintenance")

    # ── 3. SITE INFORMATION ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        meta.client_name = st.text_input(
            "Client / Owner *",
            value=meta.client_name,
            placeholder="e.g. Lifetime Fitness - San Antonio",
        )
        meta.site_name = st.text_input(
            "Site Name *",
            value=meta.site_name,
            placeholder="e.g. Riverside Commons",
        )
        meta.site_address = st.text_input(
            "Site Location / Address",
            value=meta.site_address,
            placeholder="e.g. 1234 Commerce Drive, Raleigh, NC 27601",
        )

    with col2:
        if is_inspection and is_maintenance:
            performed_label = "Inspection/Service Performed By *"
        elif is_inspection:
            performed_label = "Inspection Performed By *"
        else:
            performed_label = "Performed By *"

        meta.prepared_by = st.text_input(
            performed_label,
            value=meta.prepared_by,
            placeholder="e.g. J. Smith",
        )
        meta.report_date = st.text_input(
            "Report Date *",
            value=meta.report_date or date.today().strftime("%B %d, %Y"),
            placeholder="March 18, 2026",
        )

    # ── 4. INSPECTION / SERVICE DATE ─────────────────────────────────────────
    if is_inspection and not is_maintenance:
        date_label = "Inspection Date(s) *"
    elif is_maintenance and not is_inspection:
        date_label = "Service Date(s) *"
    else:
        date_label = "Inspection / Service Date(s) *"

    meta.inspection_date = st.text_input(
        date_label,
        value=meta.inspection_date,
        placeholder="e.g. March 14, 2026  or  March 14–15, 2026  or  March 14 & 16, 2026",
        help="Supports single dates, ranges, or multiple dates.",
    )

    # ── 5. VALIDATION ─────────────────────────────────────────────────────────
    missing = []
    if not meta.client_name:
        missing.append("Client / Owner")
    if not meta.site_name:
        missing.append("Site Name")
    if not meta.prepared_by:
        missing.append(performed_label.rstrip(" *"))
    if not meta.report_date:
        missing.append("Report Date")
    if not meta.inspection_date:
        missing.append(date_label.rstrip(" *"))

    if missing:
        st.warning(f"Required fields not yet filled: {', '.join(missing)}", icon="⚠️")
    else:
        st.success("All required fields complete.", icon="✅")

    # ── 6. NAVIGATION ─────────────────────────────────────────────────────────
    nav_buttons(next_page="systems")

"""
app/pages/page_import.py
Screen 2: Import last year's report (PDF or DOCX).

V2: Structured extraction — fields routed to correct destinations.
  - Detected header fields shown with one-click "Apply to Setup" action.
  - Photo captions parsed and stored for Systems auto-load (Issues 1, 3).
  - Section text available for write-up pre-fill (unchanged from V1).
"""

import streamlit as st
from app.session import get_project, set_page
from app.components.ui_helpers import section_header, nav_buttons, info_box
from app.services.importer import extract_text_from_file, extract_fields, extract_photo_captions


def render():
    section_header(
        "Import Last Year's Report",
        "Optional — Upload a previous report to extract reusable text. You control what gets used."
    )

    proj = get_project()

    info_box(
        "Upload a PDF or DOCX from a previous inspection or maintenance report for this site. "
        "Detected fields can be applied directly to the Setup page. "
        "Extracted captions can auto-populate systems on the Systems page. "
        "This step is completely optional — skip it to start fresh."
    )

    uploaded = st.file_uploader(
        "Upload Previous Report (PDF or DOCX)",
        type=["pdf", "docx"],
        help="File is read locally — nothing is sent to a server."
    )

    # ── Detect file cleared — undo any auto-applied fields ────────────────────
    if uploaded is None and st.session_state.get("import_has_file"):
        _clear_import(proj)
        st.rerun()

    if uploaded is not None:
        st.session_state["import_has_file"] = True

        with st.spinner("Extracting text from report…"):
            extracted = extract_text_from_file(uploaded)

        if extracted.get("error"):
            st.error(f"Could not extract text: {extracted['error']}")
        else:
            raw_text  = extracted.get("raw_text", "")
            page_info = extracted.get("page_count", "?")
            st.success(f"Extracted {page_info} page(s) of text.", icon="✅")

            # ── Structured field extraction ───────────────────────────────────
            fields   = extract_fields(raw_text)
            captions = extract_photo_captions(raw_text)

            # Store in session state for downstream pages
            st.session_state["import_extracted"] = fields
            st.session_state["imported_captions"] = captions

            proj.imported_text = extracted.get("sections", {})

            # ── Detected Fields panel ─────────────────────────────────────────
            has_fields = any(
                fields.get(k) for k in
                ("site_name", "site_address", "prepared_by", "inspection_date", "report_type")
            )
            if has_fields:
                with st.expander("📋 Detected Header Fields — click to review & apply", expanded=True):
                    st.caption(
                        "These values were extracted from the report header. "
                        "Click **Apply to Setup** to pre-fill the Setup page fields."
                    )
                    _render_field(fields, "site_name",       "Site Name")
                    _render_field(fields, "site_address",    "Site Address")
                    _render_field(fields, "prepared_by",     "Prepared By")
                    _render_field(fields, "inspection_date", "Inspection Date")
                    _render_field(fields, "report_type",     "Report Type")

                    if fields.get("system_types"):
                        st.markdown(
                            "**System Types detected:** "
                            + ", ".join(fields["system_types"])
                        )

                    st.markdown("")
                    if st.button("✅ Apply Detected Fields to Setup Page",
                                 type="primary", key="apply_fields_btn"):
                        meta = proj.meta
                        applied: dict = st.session_state.get("import_applied_fields", {})
                        _APPLY = [
                            ("site_name",       "site_name"),
                            ("site_address",    "site_address"),
                            ("prepared_by",     "prepared_by"),
                            ("inspection_date", "inspection_date"),
                            ("report_type",     "report_type"),
                        ]
                        for fld_key, meta_attr in _APPLY:
                            val = fields.get(fld_key)
                            if val and not getattr(meta, meta_attr, ""):
                                setattr(meta, meta_attr, val)
                                applied[meta_attr] = val
                        st.session_state["import_applied_fields"] = applied
                        st.success("Fields applied! Go to Setup to review.", icon="✅")

            # ── Detected Photo Captions panel ─────────────────────────────────
            if captions:
                with st.expander(
                    f"📷 {len(captions)} Photo Caption(s) Detected — "
                    f"auto-load available on Systems page",
                    expanded=False,
                ):
                    st.caption(
                        "These system IDs were extracted from photo captions. "
                        "On the Systems page, use **Auto-load Systems from Import** "
                        "to create system entries automatically. "
                        "Note: BR-1 IDs are excluded from auto-load."
                    )
                    rows = [
                        f"| {c['system_id']} | {c['system_type']} | {c['view']} |"
                        for c in captions
                    ]
                    st.markdown(
                        "| System ID | System Type | View |\n"
                        "|-----------|-------------|------|\n"
                        + "\n".join(rows)
                    )

            # ── Section text for write-up pre-fill ────────────────────────────
            st.markdown("---")
            st.markdown("### Extracted Sections")
            st.caption(
                "Use these on the Write-Ups page via 'Pre-fill from Import' to load text "
                "into write-up fields."
            )

            sections = proj.imported_text
            if sections:
                for section_name, text in sections.items():
                    with st.expander(f"📄 {section_name}", expanded=False):
                        st.text_area(
                            label="Extracted text (read-only preview)",
                            value=text,
                            height=200,
                            disabled=False,
                            key=f"import_preview_{section_name}",
                            label_visibility="collapsed"
                        )
            else:
                raw = extracted.get("raw_text", "")
                if raw:
                    st.text_area(
                        "Full extracted text",
                        value=raw,
                        height=400,
                        help="No sections were automatically identified. Review and copy text manually."
                    )
                    proj.imported_text = {"Full Document": raw}

    elif proj.imported_text:
        st.success("Previously imported text is loaded from this session.", icon="📂")
        st.caption(f"Sections available: {', '.join(proj.imported_text.keys())}")

        # Show previously extracted captions if still in session
        captions = st.session_state.get("imported_captions", [])
        if captions:
            st.info(
                f"**{len(captions)} caption(s)** from last import are ready. "
                "Go to **Systems & Photos** to auto-load them.",
                icon="📷",
            )

        if st.button("Clear imported text"):
            _clear_import(proj)
            st.rerun()
    else:
        st.markdown("---")
        st.markdown("*No report imported. Click **Next** to continue to system selection.*")

    nav_buttons(prev_page="setup", next_page="systems")


def _clear_import(proj) -> None:
    """Remove imported data and undo any fields that were applied to meta."""
    proj.imported_text = {}
    st.session_state.pop("import_extracted", None)
    st.session_state.pop("imported_captions", None)
    st.session_state.pop("import_has_file", None)

    # Undo fields that were applied from this import (only if still matching)
    applied: dict = st.session_state.pop("import_applied_fields", {})
    meta = proj.meta
    for meta_attr, applied_val in applied.items():
        if getattr(meta, meta_attr, "") == applied_val:
            setattr(meta, meta_attr, "")


def _render_field(fields: dict, key: str, label: str) -> None:
    """Display a single extracted field value."""
    val = fields.get(key, "")
    if val:
        st.markdown(
            f'<div style="font-size:0.88em;margin:2px 0">'
            f'<span style="color:#888">{label}:</span> '
            f'<span style="font-weight:600">{val}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size:0.88em;margin:2px 0;color:#aaa">'
            f'{label}: <em>not detected</em></div>',
            unsafe_allow_html=True,
        )

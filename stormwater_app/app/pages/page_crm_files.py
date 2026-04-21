"""
app/pages/page_crm_files.py
CRM File Archive — bulk upload old reports and browse all stored files.
"""

import streamlit as st
import httpx
from app.components.ui_helpers import section_header
from app.services.api_client import _headers, BACKEND_URL

_FILE_ICON = {"pdf": "📄", "docx": "📝"}

_SECTION_PRIORITY = [
    "inspection findings", "inspection summary", "maintenance summary",
    "findings and recommendations", "summary and findings",
    "recommendations", "introduction", "site description", "background",
]


def _seed_new_report(analysis: dict):
    """Populate session-state import keys so the report builder pre-fills from this analysis."""
    site_info = analysis.get("site_info", {})

    # Seed site/date fields (same shape page_setup / page_writeups expect)
    st.session_state["import_extracted"] = {
        "site_name":       site_info.get("site_name", ""),
        "site_address":    site_info.get("site_address", ""),
        "prepared_by":     site_info.get("prepared_by", ""),
        "inspection_date": site_info.get("inspection_date", ""),
        "report_type":     site_info.get("report_type", ""),
        "system_types":    site_info.get("system_types", []),
        "raw_summary":     site_info.get("raw_summary", ""),
    }

    # Seed photo captions for page_systems auto-load
    st.session_state["imported_captions"] = analysis.get("photo_captions", [])

    # Seed per-system write-ups (new key consumed by page_writeups enhanced block)
    imported_writeups = {}
    for sys in analysis.get("systems", []):
        imported_writeups[sys["system_id"].upper()] = {
            "findings":        sys.get("findings", ""),
            "recommendations": sys.get("recommendations", ""),
        }
    st.session_state["imported_writeups"] = imported_writeups

    # Navigate to Full Report setup
    st.session_state["current_page"] = "setup"


def _render_result(filename: str, result: dict):
    is_dup   = result.get("is_duplicate", False)
    analysis = result.get("analysis", {})
    site_info   = analysis.get("site_info", {})
    systems     = analysis.get("systems", [])
    captions    = analysis.get("photo_captions", [])
    recs        = analysis.get("recommendations", [])
    intro       = analysis.get("introduction", "")
    sections    = analysis.get("sections", {})
    error       = analysis.get("error") or result.get("error")

    icon   = "♻️" if is_dup else "✅"
    status = "Already archived (duplicate)" if is_dup else "Cataloged"

    with st.container(border=True):
        st.markdown(f"{icon} **{filename}** — {status}")

        if error:
            st.warning(f"Parser note: {error}", icon="⚠️")

        # ── Header metrics ────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Site",     site_info.get("site_name")       or "—")
        c2.metric("Date",     site_info.get("inspection_date") or "—")
        c3.metric("Type",     site_info.get("report_type")     or "—")
        c4.metric("Prepared", site_info.get("prepared_by")     or "—")

        if site_info.get("site_address"):
            st.caption(f"📍 {site_info['site_address']}")

        # ── System type badges ────────────────────────────────────────────
        detected_types = site_info.get("system_types", [])
        if detected_types:
            st.markdown(
                "**Systems detected:** " +
                "  ".join(
                    f'<span style="background:#f0f4f8;padding:2px 8px;border-radius:8px;'
                    f'font-size:0.82em;border:1px solid #dde">{s}</span>'
                    for s in detected_types
                ),
                unsafe_allow_html=True,
            )

        # ── Tabbed detail view ────────────────────────────────────────────
        tab_labels = ["📷 Photo Captions", "📝 Systems & Write-ups",
                      "✅ Recommendations", "📄 Full Text"]
        t_caps, t_sys, t_recs, t_text = st.tabs(tab_labels)

        # Photo Captions tab
        with t_caps:
            if captions:
                rows = "| # | System ID | Type | View |\n|---|-----------|------|------|\n"
                rows += "\n".join(
                    f"| {c['order']} | **{c['system_id']}** | {c['system_type']} | {c.get('view') or '—'} |"
                    for c in captions
                )
                st.markdown(rows)
            else:
                st.caption("No photo captions detected.")

        # Systems & Write-ups tab
        with t_sys:
            if systems:
                for sys in systems:
                    with st.expander(
                        f"**{sys['system_id']}** — {sys['system_type']}",
                        expanded=False,
                    ):
                        if sys.get("findings"):
                            st.markdown("**Findings**")
                            st.markdown(
                                f'<div style="font-size:0.88em;white-space:pre-wrap;'
                                f'line-height:1.6;padding:4px 0">{sys["findings"]}</div>',
                                unsafe_allow_html=True,
                            )
                        if sys.get("recommendations"):
                            st.markdown("**Recommendations**")
                            st.markdown(
                                f'<div style="font-size:0.88em;white-space:pre-wrap;'
                                f'line-height:1.6;padding:4px 0">{sys["recommendations"]}</div>',
                                unsafe_allow_html=True,
                            )
                        if not sys.get("findings") and not sys.get("recommendations"):
                            st.caption("No write-up text extracted for this system.")
            else:
                st.caption("No per-system analysis available.")

        # Recommendations tab
        with t_recs:
            if recs:
                for i, rec in enumerate(recs, 1):
                    st.markdown(f"{i}. {rec}")
            elif intro:
                st.caption("No standalone recommendations list detected.")
            else:
                st.caption("No recommendations extracted.")

        # Full Text tab (sections)
        with t_text:
            if intro:
                with st.expander("Introduction / Background", expanded=False):
                    st.markdown(
                        f'<div style="font-size:0.88em;white-space:pre-wrap;'
                        f'line-height:1.6;padding:4px 0">{intro}</div>',
                        unsafe_allow_html=True,
                    )
            if sections:
                ordered_keys = sorted(
                    sections.keys(),
                    key=lambda k: next(
                        (i for i, p in enumerate(_SECTION_PRIORITY) if p in k.lower()), 99
                    )
                )
                for section_name in ordered_keys:
                    text = sections[section_name].strip()
                    if not text:
                        continue
                    with st.expander(f"📄 {section_name}", expanded=False):
                        st.markdown(
                            f'<div style="font-size:0.88em;white-space:pre-wrap;'
                            f'line-height:1.6;padding:4px 0">{text}</div>',
                            unsafe_allow_html=True,
                        )
            elif not intro:
                st.caption("No text sections extracted.")

        # ── Start New Report button ───────────────────────────────────────
        st.markdown("---")
        if st.button(
            "🚀 Start New Report from This",
            key=f"seed_report_{result.get('file', {}).get('file_id', filename)}",
            help="Pre-fills the report builder with this file's site info, systems, and write-ups.",
        ):
            _seed_new_report(analysis)
            st.success("Session seeded! Navigating to report setup…")
            st.rerun()


def _upload_file(file_bytes: bytes, filename: str, client_name: str = "", site_name: str = "") -> dict | None:
    try:
        files = {"file": (filename, file_bytes, "application/octet-stream")}
        data  = {}
        if client_name:
            data["client_name"] = client_name
        if site_name:
            data["site_name"] = site_name
        r = httpx.post(
            f"{BACKEND_URL}/files/upload",
            headers=_headers(),
            files=files,
            data=data,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def _list_files() -> list[dict]:
    try:
        r = httpx.get(f"{BACKEND_URL}/files/", headers=_headers(), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _reprocess(file_id: str) -> dict | None:
    try:
        r = httpx.post(f"{BACKEND_URL}/files/{file_id}/reprocess", headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


def render():
    section_header("File Archive", "Upload old reports to catalog and search them.")

    tab_upload, tab_browse = st.tabs(["📤 Upload", "📁 Browse"])

    # ── Upload tab ────────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown(
            "Drop one or more PDFs or DOCXs below. Each file will be stored locally, "
            "text extracted, and cataloged in the database."
        )

        with st.expander("Optional: pre-assign to a client / site", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                manual_client = st.text_input(
                    "Client name (optional)", key="crm_client_override",
                    placeholder="Leave blank to auto-detect from file",
                )
            with col2:
                manual_site = st.text_input(
                    "Site name (optional)", key="crm_site_override",
                    placeholder="Leave blank to auto-detect from file",
                )

        uploaded_files = st.file_uploader(
            "Upload reports (PDF or DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            key="crm_bulk_uploader",
            label_visibility="collapsed",
        )

        if uploaded_files:
            if st.button(f"📥 Catalog {len(uploaded_files)} file(s)", type="primary"):
                results = []
                progress = st.progress(0)
                for i, f in enumerate(uploaded_files):
                    with st.spinner(f"Processing {f.name}…"):
                        result = _upload_file(
                            f.read(), f.name,
                            client_name=st.session_state.get("crm_client_override", ""),
                            site_name=st.session_state.get("crm_site_override", ""),
                        )
                        results.append((f.name, result))
                    progress.progress((i + 1) / len(uploaded_files))

                st.markdown("---")
                st.markdown("### Results")
                for filename, result in results:
                    if result and result.get("error") and not result.get("file"):
                        st.error(f"**{filename}** — {result['error']}")
                        continue
                    _render_result(filename, result)

    # ── Browse tab ────────────────────────────────────────────────────────────
    with tab_browse:
        files = _list_files()

        if not files:
            st.info("No files archived yet. Use the Upload tab to add reports.", icon="📁")
            return

        search = st.text_input(
            "🔍 Search by filename", key="crm_file_search",
            label_visibility="collapsed", placeholder="Search files…",
        )

        if search:
            files = [f for f in files if search.lower() in f["original_name"].lower()]

        st.caption(f"{len(files)} file(s)")
        st.markdown("---")

        for f in files:
            ftype = f.get("file_type", "")
            icon  = _FILE_ICON.get(ftype, "📎")
            date  = (f.get("imported_at") or "")[:10]
            col1, col2, col3 = st.columns([5, 2, 2])

            with col1:
                st.markdown(
                    f"{icon} **{f['original_name']}**  "
                    f'<span style="color:#888;font-size:0.82em">{date}</span>',
                    unsafe_allow_html=True,
                )
            with col2:
                download_url = f"{BACKEND_URL}/files/{f['file_id']}/download"
                st.markdown(
                    f'<a href="{download_url}" target="_blank" '
                    f'style="font-size:0.85em">⬇ Download</a>',
                    unsafe_allow_html=True,
                )
            with col3:
                if st.button("🔄 Re-process", key=f"reproc_{f['file_id']}", use_container_width=True):
                    with st.spinner("Re-processing…"):
                        res = _reprocess(f["file_id"])
                    if res and not res.get("error"):
                        analysis = res.get("analysis", {})
                        site_info = analysis.get("site_info", {})
                        st.success(
                            f"Site: {site_info.get('site_name') or '—'} | "
                            f"Date: {site_info.get('inspection_date') or '—'}"
                        )
                        with st.expander("View full analysis", expanded=False):
                            _render_result(f["original_name"], res)
                    else:
                        st.error(res.get("error", "Unknown error") if res else "No response")

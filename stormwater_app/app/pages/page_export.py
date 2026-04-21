"""
app/pages/page_export.py
Screen 6: Styled report preview + DOCX export.
"""

import io
import shutil
from datetime import datetime
import streamlit as st
from pathlib import Path
from PIL import Image

from app.session import get_project, get_write_up, save_project_json, ProjectSession
from app.components.ui_helpers import section_header, nav_buttons, info_box, warning_box
from app.services.report_builder import build_report


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validation_checks(proj) -> list[str]:
    """Return list of warnings to show before export."""
    issues = []
    meta = proj.meta
    if not meta.site_name:
        issues.append("Site Name is missing (Project Setup)")
    if not meta.client_name:
        issues.append("Client / Owner is missing (Project Setup)")
    if not meta.prepared_by:
        issues.append("Prepared By is missing (Project Setup)")
    if not meta.report_date:
        issues.append("Report Date is missing (Project Setup)")
    if not proj.systems:
        issues.append("No systems configured (System Selection)")
    for entry in proj.systems:
        wu = proj.write_ups.get(entry.entry_id)
        if wu:
            all_text = wu.findings + wu.recommendations + wu.maintenance_performed
            if "[" in all_text:
                issues.append(
                    f"Placeholder text remaining in {entry.system_id} write-up (Write-Ups)"
                )
    return issues


def _suggest_filename(meta) -> str:
    site = meta.site_name.replace(" ", "_").replace("/", "-") if meta.site_name else "Site"
    rtype = meta.report_type.replace(" ", "_").replace("/", "-")
    d = meta.report_date.replace(" ", "_").replace(",", "") if meta.report_date else "Date"
    return f"{site}_{rtype}_Report_{d}.docx"


def _green_bar(label: str):
    """Render a Maintenance Green section bar with accent underline — Sterling template."""
    st.markdown(
        f'<div style="background:#27AD3D;color:white;font-weight:bold;text-align:center;'
        f'padding:6px 0;margin:8px 0;font-family:Calibri,sans-serif;'
        f'border-bottom:2px solid #1E822E;letter-spacing:1px">{label}</div>',
        unsafe_allow_html=True,
    )


def _navy_bar(label: str):
    """Render a Forest Black system header bar."""
    st.markdown(
        f'<div style="background:#001e2b;color:white;font-weight:bold;padding:6px 10px;'
        f'margin:8px 0;font-family:Calibri,sans-serif;'
        f'border-left:4px solid #27AD3D">{label}</div>',
        unsafe_allow_html=True,
    )


def _snippet(text: str, max_chars: int = 300) -> str:
    """Return a truncated snippet of text."""
    if not text:
        return "*— no text entered —*"
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


# ── Preview sections ──────────────────────────────────────────────────────────

def _render_cover_preview(proj):
    meta = proj.meta

    # Approximate logo / title block
    st.markdown(
        '<div style="text-align:center;font-size:2em;font-weight:bold;'
        'color:#001e2b;font-family:Calibri,sans-serif;padding:12px 0 4px 0;'
        'border-bottom:2px solid #27AD3D;display:inline-block;width:100%">'
        'STERLING</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="text-align:center;font-size:1.1em;font-family:Calibri,sans-serif;'
        f'color:#333;padding-bottom:12px">{meta.report_type} Report<br>'
        f'<strong>{meta.site_name or "— Site Name —"}</strong></div>',
        unsafe_allow_html=True,
    )

    # Meta table
    bmp_summary = (
        ", ".join(f"{s.system_id}" for s in proj.systems) if proj.systems else "—"
    )
    rows = [
        ("Site", meta.site_name or "—"),
        ("Address", meta.site_address or "—"),
        ("Client", meta.client_name or "—"),
        ("Inspector / Performed By", meta.prepared_by or "—"),
        ("Report Date", meta.report_date or "—"),
        ("Inspection / Service Date", meta.inspection_date or "—"),
        ("Report Number", meta.report_number or "—"),
        ("BMP Systems", bmp_summary),
    ]
    table_html = (
        '<table style="width:100%;border-collapse:collapse;font-family:Calibri,sans-serif;'
        'font-size:0.9em;margin-bottom:8px">'
    )
    for label, value in rows:
        table_html += (
            f'<tr><td style="padding:4px 8px;font-weight:bold;color:#27AD3D;'
            f'width:40%;border-bottom:1px solid #e0e0e0">{label}</td>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #e0e0e0">{value}</td></tr>'
        )
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # Introduction bar + snippet
    _green_bar("INTRODUCTION")
    if meta.site_description:
        st.markdown(
            f'<div style="font-family:Calibri,sans-serif;font-size:0.9em;padding:4px 0">'
            f'{_snippet(meta.site_description, 400)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("*No overall summary entered — add it on the Write-Ups page.*")

    # Findings / Summary bar
    report_type = meta.report_type
    if report_type == "Maintenance":
        _green_bar("MAINTENANCE SUMMARY")
    elif report_type == "Inspection and Maintenance":
        _green_bar("INSPECTION AND MAINTENANCE SUMMARY")
    else:
        _green_bar("INSPECTION FINDINGS")

    if proj.systems:
        # Show first few system snippets
        shown = 0
        for entry in proj.systems:
            wu = proj.write_ups.get(entry.entry_id)
            if not wu:
                continue
            text = wu.findings or wu.maintenance_performed
            if text:
                st.markdown(
                    f'<div style="font-family:Calibri,sans-serif;font-size:0.85em;'
                    f'margin:4px 0"><strong>{entry.display_name}:</strong> '
                    f'{_snippet(text, 180)}</div>',
                    unsafe_allow_html=True,
                )
                shown += 1
            if shown >= 3:
                remaining = len(proj.systems) - shown
                if remaining > 0:
                    st.caption(f"… and {remaining} more system(s)")
                break
    else:
        st.caption("*No systems configured.*")

    _green_bar("CERTIFICATION")
    st.markdown(
        '<div style="font-family:Calibri,sans-serif;font-size:0.85em;color:#555">'
        "I certify that this report was prepared under my direction and supervision…"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_systems_preview(proj):
    meta = proj.meta
    is_inspection = meta.report_type in ("Inspection", "Inspection and Maintenance")
    is_maintenance = meta.report_type in ("Maintenance", "Inspection and Maintenance")

    if not proj.systems:
        st.caption("*No systems configured.*")
        return

    for entry in proj.systems:
        wu = proj.write_ups.get(entry.entry_id)
        _navy_bar(f"{entry.display_name}  —  {entry.system_type}")
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if wu:
                if is_inspection and wu.findings:
                    st.markdown("**Findings:**")
                    st.markdown(
                        f'<div style="font-family:Calibri,sans-serif;font-size:0.88em">'
                        f'{_snippet(wu.findings, 250)}</div>',
                        unsafe_allow_html=True,
                    )
                if is_inspection and wu.recommendations:
                    st.markdown("**Recommendations:**")
                    st.markdown(
                        f'<div style="font-family:Calibri,sans-serif;font-size:0.88em">'
                        f'{_snippet(wu.recommendations, 200)}</div>',
                        unsafe_allow_html=True,
                    )
                if is_maintenance and wu.maintenance_performed:
                    st.markdown("**Maintenance Performed:**")
                    st.markdown(
                        f'<div style="font-family:Calibri,sans-serif;font-size:0.88em">'
                        f'{_snippet(wu.maintenance_performed, 250)}</div>',
                        unsafe_allow_html=True,
                    )
                if is_maintenance and wu.post_service_condition:
                    st.markdown("**Post-Service Condition:**")
                    st.markdown(
                        f'<div style="font-family:Calibri,sans-serif;font-size:0.88em">'
                        f'{_snippet(wu.post_service_condition, 150)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("*No write-up entered.*")
        with col_b:
            photo_count = sum(1 for p in proj.photos if p.system_entry_id == entry.entry_id)
            st.metric("Photos", photo_count)
            condition_color = {
                "Good": "#27AD3D",
                "Fair": "#FFC000",
                "Poor": "#FF0000",
                "N/A": "#888888",
            }.get(entry.condition, "#888888")
            st.markdown(
                f'<div style="color:{condition_color};font-weight:bold;font-size:0.9em">'
                f'Condition: {entry.condition}</div>',
                unsafe_allow_html=True,
            )


def _render_photos_preview(proj):
    if not proj.photos:
        st.caption("*No photos added.*")
        return

    st.markdown(f"**Total photos:** {len(proj.photos)}")

    # Show photos in 2-column grid
    photo_bytes_cache = st.session_state.get("photo_bytes", {})
    sorted_photos = sorted(proj.photos, key=lambda p: p.display_order)

    cols = st.columns(2)
    col_idx = 0

    for photo in sorted_photos:
        caption = (
            photo.caption_override
            if photo.caption_override
            else photo.computed_caption()
        )

        # Try to load image bytes
        img_bytes = photo_bytes_cache.get(photo.photo_id)
        if not img_bytes and photo.filepath:
            fp = Path(photo.filepath)
            if fp.exists():
                img_bytes = fp.read_bytes()

        with cols[col_idx % 2]:
            if img_bytes:
                try:
                    from app.services.photo_service import correct_orientation_bytes
                    # Apply EXIF orientation so portrait photos display upright
                    oriented = correct_orientation_bytes(img_bytes)
                    st.image(oriented, use_container_width=True)
                except Exception:
                    st.markdown("*(image preview unavailable)*")
            else:
                # Placeholder box
                st.markdown(
                    '<div style="background:#f0f0f0;height:120px;display:flex;'
                    'align-items:center;justify-content:center;color:#888;'
                    'font-size:0.8em;border:1px dashed #ccc">'
                    "Photo not found on disk</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"**{caption}**")

        col_idx += 1


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    section_header(
        "Preview & Export",
        "Review a preview of your report, then generate the Word document."
    )

    proj = get_project()
    meta = proj.meta

    # ── Validation warnings ────────────────────────────────────────────────────
    issues = _validation_checks(proj)
    if issues:
        st.warning("**Review before exporting:**")
        for issue in issues:
            st.markdown(f"- {issue}")
        st.markdown("---")

    # ── REPORT PREVIEW ─────────────────────────────────────────────────────────
    st.markdown("## Report Preview")
    st.caption(
        "This is an approximate layout — formatting and exact spacing will differ in the DOCX."
    )

    with st.container(border=True):
        preview_tab_cover, preview_tab_systems, preview_tab_photos = st.tabs(
            ["Cover Page", "Systems", "Photos"]
        )

        with preview_tab_cover:
            _render_cover_preview(proj)

        with preview_tab_systems:
            _render_systems_preview(proj)

        with preview_tab_photos:
            _render_photos_preview(proj)

    st.markdown("---")

    # ── GENERATE REPORT ────────────────────────────────────────────────────────
    st.markdown("## Generate Report")

    col1, col2 = st.columns([2, 1])
    with col1:
        output_filename = st.text_input(
            "Output filename",
            value=_suggest_filename(meta),
            help="Saved to the /output folder in the app directory.",
        )
    with col2:
        template_path = st.text_input(
            "Template path (optional)",
            value=proj.template_path or "templates/report_template.docx",
            help="Path to your custom .docx template.",
        )
        proj.template_path = template_path

    # ── Fix #9: Photo grid choice ──────────────────────────────────────────────
    st.markdown("#### Photo Sheet Layout")
    _GRID_LABELS = {
        "2x2": "2 × 2  — 4 photos per page  (larger photos)",
        "2x3": "2 × 3  — 6 photos per page  (default, recommended)",
        "3x3": "3 × 3  — 9 photos per page  (smaller photos, more per page)",
    }
    selected_grid = st.radio(
        "Photos per page",
        options=list(_GRID_LABELS.keys()),
        format_func=lambda k: _GRID_LABELS[k],
        index=1,        # default: 2x3
        horizontal=True,
        help="Controls how many photos appear on each photo sheet page in the DOCX.",
        key="photo_grid_choice",
    )
    st.caption(
        "**2×3** is the standard Sterling layout. "
        "Choose **2×2** for larger, clearer photos; **3×3** to fit more on each page."
    )

    st.markdown("")
    if issues:
        st.info("You can still export — warnings above are reminders, not blockers.", icon="ℹ️")

    export_col, save_col = st.columns(2)

    with export_col:
        if st.button("📄 Generate & Download DOCX", type="primary", use_container_width=True):
            with st.spinner("Building report..."):
                try:
                    output_path = build_report(
                        proj,
                        output_filename,
                        template_path,
                        photo_grid=selected_grid,   # Fix #9: pass grid choice
                    )
                    st.success(f"Report saved: `{output_path}`", icon="✅")
                    st.balloons()

                    docx_bytes = Path(output_path).read_bytes()
                    st.download_button(
                        label="Download Report",
                        data=docx_bytes,
                        file_name=Path(output_path).name,
                        mime=(
                            "application/vnd.openxmlformats-officedocument"
                            ".wordprocessingml.document"
                        ),
                    )
                except Exception as e:
                    st.error(f"Export failed: {e}")
                    st.exception(e)

    with save_col:
        if st.button("Save Project", use_container_width=True):
            path = save_project_json()
            from app.services.api_client import upsert_report
            upsert_report(proj)
            st.success(f"Project saved to `{path}`")

    nav_buttons(prev_page="writeups")

    # ── REPORT STATUS & DELIVERY ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Report Status")

    status   = getattr(meta, "status", "Draft")
    revision = getattr(meta, "revision", 0)

    _STATUS_COLOR = {"Draft": "#888", "Review": "#d48b00", "Delivered": "#27AD3D"}
    _STATUS_ICON  = {"Draft": "📝", "Review": "🔍", "Delivered": "✅"}
    color = _STATUS_COLOR.get(status, "#888")
    icon  = _STATUS_ICON.get(status, "📝")

    st.markdown(
        f'<div style="display:inline-block;background:{color};color:white;'
        f'font-weight:bold;padding:4px 14px;border-radius:12px;font-size:0.95em">'
        f'{icon} {status}{f"  ·  Rev {revision}" if revision > 0 else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if status == "Delivered":
        delivered_at = getattr(meta, "delivered_at", "")
        delivered_by = getattr(meta, "delivered_by", "")
        st.markdown(
            f"Delivered **{delivered_at[:10] if delivered_at else '—'}**"
            f"{f' by {delivered_by}' if delivered_by else ''}"
        )
        st.info("This report is locked. To make changes, create a new revision.", icon="🔒")

        if st.button("📋 Create Revision", type="primary"):
            import uuid, dataclasses
            new_proj = ProjectSession(
                project_id=str(uuid.uuid4()),
                meta=dataclasses.replace(
                    proj.meta,
                    status="Draft",
                    delivered_at="",
                    delivered_by="",
                    revision=revision + 1,
                ),
                systems=list(proj.systems),
                write_ups=dict(proj.write_ups),
                photos=list(proj.photos),
                imported_text=dict(proj.imported_text),
                template_path=proj.template_path,
            )
            st.session_state.project = new_proj
            st.session_state.current_page = "setup"
            st.success(f"Revision {revision + 1} created. Editing a new draft.")
            st.rerun()

    else:
        st.caption(
            "Move through Draft → Review → Delivered to track this report's lifecycle. "
            "Delivered reports are locked — use Create Revision to make changes."
        )
        status_col, deliver_col = st.columns(2)

        with status_col:
            new_status = st.selectbox(
                "Update Status",
                ["Draft", "Review"],
                index=["Draft", "Review"].index(status) if status in ["Draft", "Review"] else 0,
                key="status_selector",
            )
            if new_status != status:
                if st.button("Apply Status", key="apply_status"):
                    proj.meta.status = new_status
                    save_project_json()
                    st.success(f"Status updated to **{new_status}**.")
                    st.rerun()

        with deliver_col:
            st.markdown("**Mark as Delivered**")
            delivered_by_input = st.text_input(
                "Delivered by",
                value=meta.prepared_by or "",
                key="deliver_by_input",
                placeholder="e.g. J. Smith",
            )
            if st.button("✅ Mark Delivered", type="primary", key="mark_delivered"):
                if not output_filename:
                    st.error("Generate a report file first before marking as Delivered.")
                else:
                    proj.meta.status       = "Delivered"
                    proj.meta.delivered_at = datetime.now().isoformat()
                    proj.meta.delivered_by = delivered_by_input or meta.prepared_by or ""

                    # Freeze an archive copy in output/
                    json_src = Path("projects") / proj.project_id / "session.json"
                    if json_src.exists():
                        archive_name = output_filename.replace(".docx", f"_DELIVERED.json")
                        try:
                            shutil.copy(str(json_src), str(Path("output") / archive_name))
                        except Exception:
                            pass

                    save_project_json()
                    st.success("Report marked as Delivered and locked. 🔒")
                    st.rerun()

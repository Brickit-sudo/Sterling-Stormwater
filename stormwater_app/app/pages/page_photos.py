"""
app/pages/page_photos.py
Screen 5: Photo upload, ordering, and caption builder.
Photos are copied into the projects folder on upload.
"""

import streamlit as st
import uuid
from pathlib import Path
from PIL import Image
import io

from app.session import get_project, Photo
from app.constants import get_components_for_system, SYSTEM_TYPES
from app.components.ui_helpers import section_header, nav_buttons, info_box, warning_box
from app.services.photo_service import save_uploaded_photo, get_photo_bytes


def _system_label_map(proj) -> dict:
    """Returns {entry_id: display_label} for all configured systems."""
    return {s.entry_id: f"{s.system_id} — {s.display_name}" for s in proj.systems}


def _renumber_captions(photos: list):
    """Reassign display_order based on current list position (1-indexed)."""
    for i, p in enumerate(photos):
        p.display_order = i + 1


def render():
    section_header(
        "Photo Manager",
        "Upload photos, assign them to systems, build captions, and set display order."
    )

    proj = get_project()

    if not proj.systems:
        warning_box("No systems configured. Add systems first before uploading photos.")
        nav_buttons(prev_page="writeups", next_page="export")
        return

    system_map = _system_label_map(proj)
    system_ids = list(system_map.keys())
    system_labels = list(system_map.values())

    info_box(
        "Upload photos in any order — use the ⬆ / ⬇ buttons to reorder. "
        "Caption fields auto-build the caption string. Override the caption manually if needed. "
        "Photos are saved into your project folder."
    )

    # ── Upload panel ──────────────────────────────────────────────────────────
    with st.expander("📤 Upload Photos", expanded=len(proj.photos) == 0):
        uploaded_files = st.file_uploader(
            "Select photos (JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Files are copied to your local projects folder."
        )

        if uploaded_files:
            default_system_idx = 0
            col1, col2 = st.columns(2)
            with col1:
                default_sys = st.selectbox(
                    "Assign to system (default for batch upload)",
                    options=system_ids,
                    format_func=lambda x: system_map[x],
                    key="batch_system"
                )
            with col2:
                # Get components for the selected system type
                sys_type = next((s.system_type for s in proj.systems if s.entry_id == default_sys), "DEFAULT")
                components = get_components_for_system(sys_type)
                default_component = st.selectbox(
                    "Default component",
                    components,
                    key="batch_component"
                )

            if st.button("➕ Add Selected Photos", type="primary"):
                existing_names = {p.filename for p in proj.photos}
                added = 0
                for uf in uploaded_files:
                    if uf.name in existing_names:
                        continue  # skip duplicates
                    saved_path = save_uploaded_photo(uf, proj.project_id)
                    sys_entry = next((s for s in proj.systems if s.entry_id == default_sys), proj.systems[0])
                    photo = Photo(
                        photo_id=str(uuid.uuid4())[:8],
                        filename=uf.name,
                        filepath=saved_path,
                        system_entry_id=default_sys,
                        system_label=sys_entry.display_name,
                        component=default_component,
                        view_number=1,
                        display_order=len(proj.photos) + 1 + added,
                    )
                    proj.photos.append(photo)
                    # Cache bytes for display
                    uf.seek(0)
                    st.session_state.photo_bytes[photo.photo_id] = uf.read()
                    added += 1

                _renumber_captions(proj.photos)
                if added:
                    st.success(f"Added {added} photo(s).")
                    st.rerun()
                else:
                    st.info("All selected photos already added.")

    # ── Photo list ────────────────────────────────────────────────────────────
    if not proj.photos:
        st.markdown("---")
        st.markdown("*No photos added yet.*")
    else:
        st.markdown(f"---")
        st.markdown(f"### Photos ({len(proj.photos)})")

        to_delete = None

        for i, photo in enumerate(proj.photos):
            col_thumb, col_fields, col_actions = st.columns([1, 4, 1])

            # ── Thumbnail ─────────────────────────────────────────────────────
            with col_thumb:
                img_bytes = st.session_state.photo_bytes.get(photo.photo_id)
                if not img_bytes and photo.filepath and Path(photo.filepath).exists():
                    img_bytes = Path(photo.filepath).read_bytes()
                    st.session_state.photo_bytes[photo.photo_id] = img_bytes

                if img_bytes:
                    try:
                        img = Image.open(io.BytesIO(img_bytes))
                        img.thumbnail((120, 90))
                        st.image(img, use_container_width=True)
                    except Exception:
                        st.markdown("🖼 *preview unavailable*")
                else:
                    st.markdown(f"🖼 `{photo.filename}`")

                st.caption(f"#{photo.display_order}")

            # ── Caption builder fields ────────────────────────────────────────
            with col_fields:
                row1col1, row1col2 = st.columns(2)
                with row1col1:
                    # System assignment
                    try:
                        sys_idx = system_ids.index(photo.system_entry_id)
                    except ValueError:
                        sys_idx = 0
                    new_sys = st.selectbox(
                        "System",
                        options=system_ids,
                        format_func=lambda x: system_map[x],
                        index=sys_idx,
                        key=f"photo_sys_{photo.photo_id}",
                        label_visibility="visible"
                    )
                    if new_sys != photo.system_entry_id:
                        photo.system_entry_id = new_sys
                        sys_entry = next((s for s in proj.systems if s.entry_id == new_sys), None)
                        if sys_entry:
                            photo.system_label = sys_entry.display_name

                with row1col2:
                    # Component dropdown (driven by system type)
                    sys_entry = next((s for s in proj.systems if s.entry_id == photo.system_entry_id), None)
                    sys_type = sys_entry.system_type if sys_entry else "DEFAULT"
                    components = get_components_for_system(sys_type)
                    comp_idx = components.index(photo.component) if photo.component in components else 0
                    photo.component = st.selectbox(
                        "Component",
                        components,
                        index=comp_idx,
                        key=f"photo_comp_{photo.photo_id}"
                    )

                row2col1, row2col2, row2col3 = st.columns([1, 1, 2])
                with row2col1:
                    photo.view_number = st.number_input(
                        "View #",
                        min_value=1,
                        max_value=99,
                        value=photo.view_number,
                        key=f"photo_view_{photo.photo_id}"
                    )
                with row2col2:
                    photo.include_date = st.checkbox(
                        "Include date",
                        value=photo.include_date,
                        key=f"photo_incdate_{photo.photo_id}"
                    )
                with row2col3:
                    if photo.include_date:
                        photo.photo_date = st.text_input(
                            "Date",
                            value=photo.photo_date,
                            key=f"photo_date_{photo.photo_id}",
                            placeholder="March 14, 2026"
                        )

                # Caption preview + override
                computed = photo.computed_caption()
                photo.caption_override = st.text_input(
                    "Caption (auto-built — edit to override)",
                    value=photo.caption_override or computed,
                    key=f"photo_cap_{photo.photo_id}",
                    help="Leave blank to use the auto-built caption, or type your own."
                )

                # Show what will actually be used
                final_caption = photo.caption_override if photo.caption_override != computed else computed
                st.caption(f"→ {final_caption}")

            # ── Reorder / delete ──────────────────────────────────────────────
            with col_actions:
                st.markdown("<br>", unsafe_allow_html=True)
                if i > 0:
                    if st.button("⬆", key=f"up_{photo.photo_id}", help="Move up"):
                        proj.photos[i], proj.photos[i-1] = proj.photos[i-1], proj.photos[i]
                        _renumber_captions(proj.photos)
                        st.rerun()
                if i < len(proj.photos) - 1:
                    if st.button("⬇", key=f"dn_{photo.photo_id}", help="Move down"):
                        proj.photos[i], proj.photos[i+1] = proj.photos[i+1], proj.photos[i]
                        _renumber_captions(proj.photos)
                        st.rerun()
                if st.button("🗑", key=f"del_{photo.photo_id}", help="Remove photo"):
                    to_delete = photo.photo_id

            st.markdown("---")

        if to_delete:
            proj.photos = [p for p in proj.photos if p.photo_id != to_delete]
            st.session_state.photo_bytes.pop(to_delete, None)
            _renumber_captions(proj.photos)
            st.rerun()

        # ── Bulk tools ────────────────────────────────────────────────────────
        with st.expander("🔧 Bulk Caption Tools", expanded=False):
            st.markdown("**Reassign all photos to a system:**")
            bulk_sys = st.selectbox(
                "Reassign all to system",
                options=system_ids,
                format_func=lambda x: system_map[x],
                key="bulk_reassign_sys"
            )
            if st.button("Apply to all photos", key="bulk_apply"):
                sys_entry = next((s for s in proj.systems if s.entry_id == bulk_sys), None)
                for p in proj.photos:
                    p.system_entry_id = bulk_sys
                    if sys_entry:
                        p.system_label = sys_entry.display_name
                    p.caption_override = ""  # reset overrides
                st.success("Bulk reassignment applied.")
                st.rerun()

            st.markdown("**Renumber all captions:**")
            if st.button("Reset caption numbers to current order"):
                _renumber_captions(proj.photos)
                for p in proj.photos:
                    p.caption_override = ""
                st.success("Captions renumbered.")
                st.rerun()

    nav_buttons(prev_page="writeups", next_page="export")

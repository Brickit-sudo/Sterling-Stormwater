"""
app/pages/page_systems.py
Screen 2: Add systems, upload photos per system, name photos, add notes.
Each system is added via the quick-add row, then configured inline.
Photos are uploaded per system; a dialog handles per-photo captioning.
"""

import streamlit as st
import uuid
from pathlib import Path
from PIL import Image
import io

from app.session import get_project, SystemEntry, WriteUp, Photo
from app.constants import SYSTEM_TYPES, SYSTEM_ID_PREFIX, CONDITION_RATINGS, get_components_for_system, PS_SEVERITY_TAGS, PS_ISSUE_TAGS
from app.components.ui_helpers import section_header, nav_buttons
from app.services.photo_service import save_uploaded_photo, correct_orientation_bytes, UPLOAD_TYPES

# ── System-type → relevant issue tags (Full Report field notes) ───────────────
_FR_SYSTEM_ISSUES: dict[str, list[str]] = {
    "Bioretention Basin":           ['>4" Sediment', 'Excess Vegetation', 'Standing Water', 'Erosion Present', 'Partially Obstructed', 'Debris Present'],
    "Rain Garden":                  ['>4" Sediment', 'Excess Vegetation', 'Standing Water', 'Erosion Present', 'Debris Present'],
    "Underdrained Soil Filter (USF)": ['>4" Sediment', 'Standing Water', 'Erosion Present', 'Partially Obstructed', 'Structural Damage'],
    "Infiltration Cell":            ['>4" Sediment', 'Standing Water', 'Erosion Present', 'Debris Present'],
    "Infiltration Trench":          ['>4" Sediment', 'Standing Water', 'Erosion Present', 'Partially Obstructed'],
    "Stormwater Pond":              ['Sheen on Water', 'Excess Vegetation', 'Standing Water', 'Erosion Present', 'Debris Present', 'Structural Damage'],
    "Wet Pond":                     ['Sheen on Water', 'Excess Vegetation', 'Erosion Present', 'Debris Present', 'Structural Damage'],
    "Retention Pond":               ['Sheen on Water', 'Excess Vegetation', 'Erosion Present', 'Debris Present'],
    "Typical Catch Basin":          ['>4" Sediment', 'Partially Obstructed', 'Fully Obstructed', 'Detached Hood', 'Missing Hardware', 'Debris Present'],
    "Typical Catch Basin With Insert": ['>4" Sediment', 'Partially Obstructed', 'Fully Obstructed', 'Detached Hood', 'Missing Hardware'],
    "Typical Field Inlet":          ['>4" Sediment', 'Partially Obstructed', 'Debris Present', 'Structural Damage'],
    "Outfall Area":                 ['Sheen on Water', 'Erosion Present', 'Debris Present', 'Partially Obstructed', 'Structural Damage'],
    "Permeable Pavement":           ['>4" Sediment', 'Standing Water', 'Excess Vegetation', 'Structural Damage'],
    "Porous Pavement":              ['>4" Sediment', 'Standing Water', 'Excess Vegetation', 'Structural Damage'],
    "Grassy Drainage Channel":      ['Excess Vegetation', 'Erosion Present', 'Debris Present', 'Standing Water'],
    "Isolator Row":                 ['>4" Sediment', 'Partially Obstructed', 'Fully Obstructed', 'Structural Damage'],
}

def _get_fr_issues(system_type: str) -> list[str]:
    """Return issue tags relevant to *system_type*, falling back to all tags."""
    return _FR_SYSTEM_ISSUES.get(system_type, PS_ISSUE_TAGS)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_existing(systems: list, system_type: str) -> int:
    return sum(1 for s in systems if s.system_type == system_type)


def _suggest_id(system_type: str, systems: list) -> str:
    """
    Return the next available system ID for the given system_type.

    Strategy (guardrails so manual edits never break future numbering):
      1. Look at all existing IDs that start with the correct prefix.
      2. Extract the trailing numeric part from each.
      3. Next = max(found) + 1   (not count, to survive deletions / manual edits).
      4. Walk forward until a candidate that isn't already taken is found.

    Examples:
      BR-1, BR-2 exist → suggest BR-3
      BR-1 deleted → BR-2 exists → suggest BR-3  (not BR-2 again)
      BR-1 manually renamed "BC-1" → prefix scan finds no BR-N → suggest BR-1
    """
    prefix = SYSTEM_ID_PREFIX.get(system_type, "SYS")
    all_ids = {s.system_id for s in systems if s.system_id}

    # Collect numeric suffixes already used for this exact prefix
    used_nums: list[int] = []
    for s in systems:
        sid = s.system_id or ""
        if sid.upper().startswith(f"{prefix.upper()}-"):
            try:
                used_nums.append(int(sid.rsplit("-", 1)[-1]))
            except ValueError:
                pass  # non-numeric suffix — ignore, don't crash

    next_num = max(used_nums, default=0) + 1

    # Walk forward until we find an ID not already in use
    candidate = f"{prefix}-{next_num}"
    while candidate in all_ids:
        next_num += 1
        candidate = f"{prefix}-{next_num}"

    return candidate


def _renumber_photos(photos: list):
    for i, p in enumerate(photos):
        p.display_order = i + 1


def _photos_for(proj, entry_id: str) -> list:
    return [p for p in proj.photos if p.system_entry_id == entry_id]


# ── Photo naming dialog ───────────────────────────────────────────────────────

@st.dialog("📸 Name Photos", width="large")
def _photo_name_dialog(entry_id: str):
    proj = get_project()
    entry = next((s for s in proj.systems if s.entry_id == entry_id), None)
    if not entry:
        st.error("System not found.")
        return

    photos = _photos_for(proj, entry_id)
    if not photos:
        st.info("No photos uploaded for this system yet.")
        if st.button("Close"):
            st.rerun()
        return

    n = len(photos)
    idx_key = f"dlg_idx_{entry_id}"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    idx = max(0, min(st.session_state[idx_key], n - 1))

    photo = photos[idx]
    pid          = photo.photo_id
    comp_key     = f"dlg_comp_{pid}"
    cap_key      = f"dlg_cap_{pid}"
    prev_cap_key = f"dlg_prev_computed_{pid}"
    notes_key    = f"dlg_notes_{pid}"

    relevant_issues = _get_fr_issues(entry.system_type)
    ISSUE_COLS = 4

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"**{entry.display_name}** — Photo {idx + 1} of {n}")
    st.progress((idx + 1) / n)
    st.markdown("---")

    # ── on_change: update caption when Component changes ─────────────────────
    def _sync_caption(ph=photo, ck=comp_key, capk=cap_key, prevk=prev_cap_key):
        new_comp = st.session_state.get(ck, ph.component)
        ph.component = new_comp
        new_computed = ph.computed_caption()
        prev_computed = st.session_state.get(prevk, "")
        current_val   = st.session_state.get(capk, "")
        if not current_val or current_val == prev_computed:
            st.session_state[capk] = new_computed

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_img, col_fields = st.columns([1, 2])

    with col_img:
        img_bytes = st.session_state.photo_bytes.get(pid)
        if not img_bytes and photo.filepath and Path(photo.filepath).exists():
            img_bytes = Path(photo.filepath).read_bytes()
            st.session_state.photo_bytes[pid] = img_bytes
        if img_bytes:
            try:
                oriented = correct_orientation_bytes(img_bytes)
                st.image(oriented, use_container_width=True)
            except Exception:
                st.markdown("🖼 *preview unavailable*")
        else:
            st.markdown(f"🖼 `{photo.filename}`")
        st.caption(f"#{photo.display_order} · {photo.filename}")

    with col_fields:
        components   = get_components_for_system(entry.system_type)
        comp_idx     = components.index(photo.component) if photo.component in components else 0
        base_caption = f"({photo.display_order}) {photo.system_label} - "

        if cap_key not in st.session_state:
            st.session_state[cap_key] = photo.caption_override or base_caption
        if prev_cap_key not in st.session_state:
            st.session_state[prev_cap_key] = st.session_state[cap_key]

        photo.component = st.selectbox(
            "Component", components, index=comp_idx,
            key=comp_key, on_change=_sync_caption,
        )

        row1, row2 = st.columns(2)
        with row1:
            photo.view_number = st.number_input(
                "View #", min_value=1, max_value=99,
                value=photo.view_number, key=f"dlg_view_{pid}",
            )
        with row2:
            photo.include_date = st.checkbox(
                "Include date", value=photo.include_date, key=f"dlg_incdate_{pid}",
            )
        if photo.include_date:
            photo.photo_date = st.text_input(
                "Date", value=photo.photo_date,
                key=f"dlg_date_{pid}", placeholder="March 14, 2026",
            )

        # ── Caption ──────────────────────────────────────────────────────────
        st.session_state[prev_cap_key] = st.session_state.get(cap_key, base_caption)
        photo.caption_override = st.text_input("Caption (edit to override)", key=cap_key)
        st.caption(f"→ {st.session_state.get(cap_key, base_caption)}")

        # ── Field Notes ──────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
            'letter-spacing:0.08em;margin:8px 0 3px">Field Notes</div>',
            unsafe_allow_html=True,
        )

        sev_cols = st.columns(len(PS_SEVERITY_TAGS))
        for si, sev in enumerate(PS_SEVERITY_TAGS):
            with sev_cols[si]:
                if st.button(sev, key=f"dlg_sev_{pid}_{si}", use_container_width=True):
                    sep = ", " if photo.notes.strip() else ""
                    photo.notes = photo.notes.rstrip() + sep + sev
                    st.session_state[notes_key] = photo.notes
                    st.rerun()

        for row_start in range(0, len(relevant_issues), ISSUE_COLS):
            chunk    = relevant_issues[row_start : row_start + ISSUE_COLS]
            iss_cols = st.columns(ISSUE_COLS)
            for ci, tag in enumerate(chunk):
                with iss_cols[ci]:
                    if st.button(tag, key=f"dlg_tag_{pid}_{row_start}_{ci}",
                                 use_container_width=True):
                        sep = ", " if photo.notes.strip() else ""
                        photo.notes = photo.notes.rstrip() + sep + tag
                        st.session_state[notes_key] = photo.notes
                        st.rerun()

        photo.notes = st.text_area(
            "Notes", value=photo.notes, key=notes_key,
            height=60, placeholder="Field observations for this photo…",
            label_visibility="collapsed",
        )

    st.markdown("---")

    # ── Commit helper — called before any navigation ──────────────────────────
    def _commit():
        """Write current widget state into the photo object and build caption."""
        cap_val = st.session_state.get(cap_key, "")
        if not cap_val or cap_val == base_caption:
            # Component may not have triggered on_change if it was already set;
            # build the full caption from the current component/view state.
            photo.caption_override = ""          # clear so computed_caption uses fields
            photo.caption_override = photo.computed_caption()
        else:
            photo.caption_override = cap_val
        photo.notes = st.session_state.get(notes_key, photo.notes)

    # ── Navigation row ────────────────────────────────────────────────────────
    nav_l, nav_mid, nav_r = st.columns([1, 3, 1])

    with nav_l:
        if idx > 0:
            if st.button("← Prev", use_container_width=True, key="dlg_prev"):
                _commit()
                st.session_state[idx_key] = idx - 1
                st.rerun()

    with nav_mid:
        st.markdown(
            f'<div style="text-align:center;padding-top:6px;font-size:0.85em;color:#888">'
            f'{idx + 1} / {n}</div>',
            unsafe_allow_html=True,
        )

    with nav_r:
        if idx < n - 1:
            if st.button("Next →", type="primary", use_container_width=True, key="dlg_next"):
                _commit()
                st.session_state[idx_key] = idx + 1
                st.rerun()
        else:
            if st.button("✅ Done", type="primary", use_container_width=True, key="dlg_done"):
                _commit()
                st.session_state.pop(idx_key, None)
                st.session_state.pop("photo_dialog_for", None)
                st.rerun()


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    section_header(
        "Systems & Photos",
        "Add each stormwater system, upload photos, and enter field notes."
    )

    proj = get_project()

    # ── Auto-load from Import (Issues 3 & 4) ─────────────────────────────────
    imported_captions = st.session_state.get("imported_captions", [])
    if imported_captions:
        with st.expander(
            f"📥 Auto-load {len(imported_captions)} System(s) from Import",
            expanded=False,
        ):
            st.caption(
                "These system IDs were extracted from the imported report's photo captions. "
                "Click **Load All** to create system entries automatically. "
                "Systems already added (matching system_id) are skipped. "
                "BR-1 IDs are excluded — add them manually if needed."
            )

            # Preview table
            rows_html = "".join(
                f'<tr><td style="padding:2px 8px">{c["system_id"]}</td>'
                f'<td style="padding:2px 8px;color:#555">{c["system_type"]}</td></tr>'
                for c in imported_captions
                if c["system_id"].upper() != "BR-1"   # Issue 4: BR-1 exclusion
            )
            excluded_br1 = [c for c in imported_captions if c["system_id"].upper() == "BR-1"]
            st.markdown(
                f'<table style="font-size:0.85em;border-collapse:collapse">'
                f'<tr><th style="padding:2px 8px;text-align:left">ID</th>'
                f'<th style="padding:2px 8px;text-align:left">System Type</th></tr>'
                f'{rows_html}</table>',
                unsafe_allow_html=True,
            )
            if excluded_br1:
                st.caption(
                    f"⚠️ {len(excluded_br1)} BR-1 ID(s) excluded from auto-load "
                    "— add manually if required."
                )

            if st.button("📥 Load All Systems", type="primary",
                         key="autoload_systems_btn"):
                existing_ids = {s.system_id.upper() for s in proj.systems}
                added = 0
                for cap in imported_captions:
                    sid_upper = cap["system_id"].upper()

                    # Issue 4: skip BR-1 IDs in autoload sequence
                    if sid_upper == "BR-1":
                        continue

                    # Skip if already added
                    if sid_upper in existing_ids:
                        continue

                    # Map extracted system_type to a known SYSTEM_TYPES entry
                    matched_type = cap["system_type"]
                    for known in SYSTEM_TYPES:
                        if cap["system_type"].lower() in known.lower() or \
                                known.lower() in cap["system_type"].lower():
                            matched_type = known
                            break

                    entry = SystemEntry(
                        entry_id=str(uuid.uuid4())[:8],
                        system_type=matched_type,
                        system_id=cap["system_id"],
                        display_name=f"{matched_type} {cap['system_id']}",
                        condition="Good",
                    )
                    proj.systems.append(entry)
                    proj.write_ups[entry.entry_id] = WriteUp(entry_id=entry.entry_id)
                    existing_ids.add(sid_upper)
                    added += 1

                if added:
                    st.success(f"Added {added} system(s).", icon="✅")
                    st.rerun()
                else:
                    st.info("All detected systems are already added.")

    # ── Quick-add row ─────────────────────────────────────────────────────────
    st.markdown("### Add a System")
    col_type, col_id, col_btn = st.columns([4, 2, 1])
    with col_type:
        selected_type = st.selectbox(
            "System Type",
            SYSTEM_TYPES,
            key="new_system_type",
            label_visibility="collapsed"
        )
    with col_id:
        suggested_id = _suggest_id(selected_type, proj.systems)
        new_id_input = st.text_input(
            "System ID",
            value=suggested_id,
            key="new_system_id",
            label_visibility="collapsed",
            placeholder="e.g. BR-1"
        )
    with col_btn:
        if st.button("➕ Add", type="primary", use_container_width=True):
            count = _count_existing(proj.systems, selected_type) + 1
            entry = SystemEntry(
                entry_id=str(uuid.uuid4())[:8],
                system_type=selected_type,
                system_id=new_id_input or suggested_id,
                display_name=f"{selected_type} {count}",
                condition="Good",
            )
            proj.systems.append(entry)
            proj.write_ups[entry.entry_id] = WriteUp(entry_id=entry.entry_id)
            st.session_state[f"expand_{entry.entry_id}"] = True
            st.rerun()

    st.markdown("---")

    # ── Open photo dialog if flagged ──────────────────────────────────────────
    dialog_target = st.session_state.get("photo_dialog_for")
    if dialog_target:
        _photo_name_dialog(dialog_target)

    # ── System cards ──────────────────────────────────────────────────────────
    if not proj.systems:
        st.markdown("*No systems added yet. Use the row above to add your first system.*")
    else:
        to_delete = None

        for i, entry in enumerate(proj.systems):
            photo_count = len(_photos_for(proj, entry.entry_id))
            label = (
                f"**{entry.system_id}** — {entry.system_type}  "
                f"|  {entry.condition}  |  {photo_count} photo(s)"
            )

            default_expanded = st.session_state.get(f"expand_{entry.entry_id}", False)
            with st.expander(label, expanded=default_expanded):

                # ── System fields ──────────────────────────────────────────
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    entry.display_name = st.text_input(
                        "Display Name",
                        value=entry.display_name,
                        key=f"sys_name_{entry.entry_id}",
                        help="Appears in report headings"
                    )
                    entry.system_id = st.text_input(
                        "System ID",
                        value=entry.system_id,
                        key=f"sys_id_{entry.entry_id}",
                        help="Used in write-ups and captions"
                    )
                with c2:
                    entry.system_type = st.selectbox(
                        "System Type",
                        SYSTEM_TYPES,
                        index=SYSTEM_TYPES.index(entry.system_type) if entry.system_type in SYSTEM_TYPES else 0,
                        key=f"sys_type_{entry.entry_id}"
                    )
                    cond_idx = CONDITION_RATINGS.index(entry.condition) if entry.condition in CONDITION_RATINGS else 0
                    entry.condition = st.selectbox(
                        "Overall Condition",
                        CONDITION_RATINGS,
                        index=cond_idx,
                        key=f"sys_cond_{entry.entry_id}"
                    )
                with c3:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if i > 0 and st.button("⬆", key=f"up_{entry.entry_id}", help="Move up"):
                        proj.systems[i], proj.systems[i-1] = proj.systems[i-1], proj.systems[i]
                        st.rerun()
                    if i < len(proj.systems) - 1 and st.button("⬇", key=f"dn_{entry.entry_id}", help="Move down"):
                        proj.systems[i], proj.systems[i+1] = proj.systems[i+1], proj.systems[i]
                        st.rerun()

                st.markdown("---")

                # ── Photo upload ───────────────────────────────────────────
                st.markdown("**Photos**")
                uploaded_files = st.file_uploader(
                    f"Upload photos for {entry.system_id}",
                    type=UPLOAD_TYPES,        # includes HEIC/HEIF if pillow-heif installed
                    accept_multiple_files=True,
                    key=f"upload_{entry.entry_id}",
                    label_visibility="collapsed"
                )

                if uploaded_files:
                    if st.button(
                        f"➕ Add {len(uploaded_files)} photo(s) to {entry.system_id}",
                        key=f"add_photos_{entry.entry_id}",
                        type="primary"
                    ):
                        # BUG FIX: previously checked filenames across ALL systems,
                        # so uploading IMG_001.jpg to System 2 after System 1 already
                        # had it would silently skip it.  Now we only dedup within
                        # the current system so each system gets its own photos.
                        existing_names_this_system = {
                            p.filename for p in proj.photos
                            if p.system_entry_id == entry.entry_id
                        }
                        added = 0
                        heic_errors: list[str] = []

                        for uf in uploaded_files:
                            if uf.name in existing_names_this_system:
                                continue   # skip true duplicate within this system only
                            try:
                                saved_path = save_uploaded_photo(uf, proj.project_id)
                            except ValueError as exc:
                                # Raised for HEIC when pillow-heif is not installed
                                heic_errors.append(str(exc))
                                continue
                            except Exception as exc:
                                st.error(f"Could not save **{uf.name}**: {exc}")
                                continue

                            components = get_components_for_system(entry.system_type)
                            photo = Photo(
                                photo_id=str(uuid.uuid4())[:8],
                                filename=uf.name,
                                filepath=saved_path,
                                system_entry_id=entry.entry_id,
                                system_label=entry.display_name,
                                component=components[0] if components else "Overall View",
                                view_number=1,
                                display_order=len(proj.photos) + 1 + added,
                            )
                            proj.photos.append(photo)
                            uf.seek(0)
                            st.session_state.photo_bytes[photo.photo_id] = uf.read()
                            added += 1

                        if heic_errors:
                            st.warning(
                                "**HEIC upload failed** — `pillow-heif` is not installed.\n\n"
                                "To enable HEIC/iPhone photo support, run this once in your "
                                "terminal then restart the app:\n\n"
                                "```\npip install pillow-heif\n```",
                                icon="📷",
                            )

                        _renumber_photos(proj.photos)
                        if added:
                            st.session_state.photo_dialog_for = entry.entry_id
                            st.rerun()
                        elif not heic_errors:
                            st.info("All selected photos are already added to this system.")

                # Show existing photo thumbnails
                sys_photos = _photos_for(proj, entry.entry_id)
                if sys_photos:
                    thumb_cols = st.columns(min(len(sys_photos), 5))
                    for j, photo in enumerate(sys_photos):
                        with thumb_cols[j % 5]:
                            img_bytes = st.session_state.photo_bytes.get(photo.photo_id)
                            if not img_bytes and photo.filepath and Path(photo.filepath).exists():
                                img_bytes = Path(photo.filepath).read_bytes()
                                st.session_state.photo_bytes[photo.photo_id] = img_bytes
                            if img_bytes:
                                try:
                                    # Orientation-corrected — no tiny thumbnail downscale
                                    oriented = correct_orientation_bytes(img_bytes)
                                    st.image(oriented, use_container_width=True)
                                except Exception:
                                    st.markdown("🖼")
                            cap = photo.caption_override or photo.computed_caption()
                            st.caption(f"#{photo.display_order} {cap[:28]}{'…' if len(cap) > 28 else ''}")

                    col_name, col_clear = st.columns([2, 1])
                    with col_name:
                        if st.button(
                            f"✏️ Name / Edit Captions ({photo_count})",
                            key=f"name_btn_{entry.entry_id}",
                            use_container_width=True
                        ):
                            st.session_state.photo_dialog_for = entry.entry_id
                            st.rerun()
                    with col_clear:
                        if st.button("🗑 Remove All Photos", key=f"clear_photos_{entry.entry_id}"):
                            proj.photos = [p for p in proj.photos if p.system_entry_id != entry.entry_id]
                            _renumber_photos(proj.photos)
                            st.rerun()

                st.markdown("---")

                # ── Notes ──────────────────────────────────────────────────
                st.markdown("**Field Notes**")
                entry.notes = st.text_area(
                    "Notes",
                    value=entry.notes,
                    height=100,
                    key=f"sys_notes_{entry.entry_id}",
                    label_visibility="collapsed",
                    placeholder=(
                        "Location, conditions, anything to reference when writing the summary. "
                        "e.g. 'Northwest parking lot island, ~1.2 ac. Outlet partially blocked by debris.'"
                    )
                )

                # ── Remove system ──────────────────────────────────────────
                st.markdown("")
                if st.button(f"🗑 Remove {entry.system_id}", key=f"del_{entry.entry_id}"):
                    to_delete = entry.entry_id

        if to_delete:
            proj.systems = [s for s in proj.systems if s.entry_id != to_delete]
            proj.write_ups.pop(to_delete, None)
            proj.photos = [p for p in proj.photos if p.system_entry_id != to_delete]
            _renumber_photos(proj.photos)
            st.rerun()

    nav_buttons(prev_page="setup", next_page="writeups")

"""
app/pages/page_photosheet.py
Photosheet builder — upload → organize → export.

Organize-step layout:
  1. Horizontal draggable thumbnail strip (full width, top)
  2. Caption builder + large photo preview (side by side below strip)

Caption builder is split into two tiers:
  ┌─ CURRENT SYSTEM (persistent) ─────────────────────────────────────────────┐
  │  System Type (dropdown)  ·  System Name/ID (text)  ·  [✕ Clear]           │
  │  Auto-applied to every photo captioned from this point.                    │
  └────────────────────────────────────────────────────────────────────────────┘
  ┌─ Photo Caption (per-photo) ────────────────────────────────────────────────┐
  │  View Type quick-pick buttons                                              │
  │  Annotation text input                                                     │
  │  Live caption preview                                                      │
  └────────────────────────────────────────────────────────────────────────────┘

Caption format:   System Type – System Name – View Type – Annotation
DOCX output:     (N) System Type – System Name – View Type – Annotation

State model:
  Global (session): ps_ctx_sys_type, ps_ctx_sys_name
  Per-photo:        caption_view, caption_note, notes
"""

import io
import json
import uuid
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from app.session import (
    PhotosheetPhoto,
    ps_save_draft,
    ps_load_draft,
    ps_find_latest_draft,
    ps_sync_widget_states,
)
from app.constants import (
    PS_SYSTEM_TYPES,
    PS_SYSTEM_ORDER,
    PS_VIEW_PRIORITY,
    PS_SEVERITY_TAGS,
    PS_ISSUE_TAGS,
    PS_LAYOUTS,
    PS_SYS_PREFIX,
)
from app.components.sortable_strip import sortable_photo_strip

# ── Quick view token system — sectioned ───────────────────────────────────────
# Tokens are composable words/phrases appended (space-joined) to build a view
# description.  They live in three named sections that map to labelled rows.
# The config is user-editable and saved to disk.

_TOKENS_CONFIG = (
    Path(__file__).parent.parent.parent / "config" / "quick_view_tokens.json"
)

# Section key → (display label, tokens)
_DEFAULT_SECTIONS: dict[str, tuple[str, list[str]]] = {
    "view_prefix": ("View",    ["View", "View of"]),
    "features":    ("Feature", ["Inlet", "Outlet", "Inlet Area", "Inside",
                                 "Surface", "Overall", "Maintenance", "Pipe"]),
    "numbers":     ("#",       ["1", "2", "3", "4"]),
}


def _load_sections() -> dict[str, tuple[str, list[str]]]:
    """
    Read sectioned token config from disk.
    Format on disk:  {"view_prefix": ["View", "View of"], "features": [...], ...}
    Labels are NOT stored — they come from _DEFAULT_SECTIONS.
    Falls back to defaults if file missing, empty, or invalid.
    """
    try:
        if _TOKENS_CONFIG.exists():
            raw = json.loads(_TOKENS_CONFIG.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw:
                out: dict[str, tuple[str, list[str]]] = {}
                for key, default_label_tokens in _DEFAULT_SECTIONS.items():
                    label = default_label_tokens[0]
                    tokens = [str(t) for t in raw.get(key, default_label_tokens[1]) if str(t).strip()]
                    out[key] = (label, tokens)
                # Carry any extra user-created sections
                for key, val in raw.items():
                    if key not in out and isinstance(val, list):
                        out[key] = (key.replace("_", " ").title(),
                                    [str(t) for t in val if str(t).strip()])
                return out
    except Exception:
        pass
    return {k: (lbl, list(toks)) for k, (lbl, toks) in _DEFAULT_SECTIONS.items()}


def _save_sections(sections: dict[str, tuple[str, list[str]]]) -> None:
    """Persist sections to disk as {key: [tokens]} (labels are implicit)."""
    try:
        _TOKENS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: list(toks) for k, (_, toks) in sections.items()}
        _TOKENS_CONFIG.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _ensure_tokens() -> None:
    """Lazy-load sectioned tokens into session state on first organize render."""
    if "ps_quick_sections" not in st.session_state:
        st.session_state.ps_quick_sections = _load_sections()

# ── Accepted image extensions ─────────────────────────────────────────────────
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


# ── Thumbnail helper ──────────────────────────────────────────────────────────

def _make_thumb(raw_bytes: bytes, width_px: int = 140) -> bytes:
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img = ImageOps.exif_transpose(img)
        ratio = width_px / img.width
        new_h = max(1, int(img.height * ratio))
        img = img.resize((width_px, new_h), Image.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return buf.getvalue()
    except Exception:
        return b""


# ── Photo order helpers ────────────────────────────────────────────────────────

def _renumber(photos: list):
    """Assign globalOrder and recompute group_order within each system_id bucket."""
    for i, p in enumerate(photos):
        p.order = i + 1
    counters: dict = {}
    for p in photos:
        sid = p.system_id or "_uncat"
        counters[sid] = counters.get(sid, 0) + 1
        p.group_order = counters[sid]


def _get_selected_photo():
    """Return (photo, index) for ps_selected_pid, defaulting to first photo."""
    pid = st.session_state.get("ps_selected_pid", "")
    photos = st.session_state.ps_photos
    if not photos:
        return None, 0
    if pid:
        for i, p in enumerate(photos):
            if p.photo_id == pid:
                return p, i
    st.session_state.ps_selected_pid = photos[0].photo_id
    return photos[0], 0


def _apply_reorder(new_order: list):
    """Reorder ps_photos to match the list of photo_ids returned by the strip."""
    photos = st.session_state.ps_photos
    id_map = {p.photo_id: p for p in photos}
    reordered = [id_map[pid] for pid in new_order if pid in id_map]
    remaining = [p for p in photos if p.photo_id not in set(new_order)]
    st.session_state.ps_photos = reordered + remaining
    _renumber(st.session_state.ps_photos)
    ps_save_draft()


# ── Caption helpers ───────────────────────────────────────────────────────────

def _rebuild_caption(photo) -> str:
    """
    Build the caption string from the photo's components:
      System Type – System Name – View Type – Annotation

    "Uncategorized" system is treated as unset and omitted.
    Empty parts are always skipped.
    Falls back to the stored photo.caption if every component is blank
    (preserves captions imported from old drafts).
    """
    sys_part = photo.system if photo.system not in ("", "Uncategorized") else ""
    parts = [
        p.strip()
        for p in [sys_part, photo.caption_id, photo.caption_view, photo.caption_note]
        if p.strip()
    ]
    if parts:
        return " \u2013 ".join(parts)
    return photo.caption  # fall back to whatever was stored


def _commit_caption(photo):
    """Write the rebuilt caption to photo.caption and autosave."""
    photo.caption = _rebuild_caption(photo)
    ps_save_draft()


# ── Context panel callbacks (system type/name — global, not per-photo) ────────

def _on_ctx_sys_type_change():
    """
    Fires when the user selects a system type in the context panel.
    1. Updates ps_ctx_sys_type.
    2. Auto-fills ps_ctx_sys_name with the standard prefix if name was blank
       or was a previous auto-filled prefix (so typing a custom name is safe).
    3. Applies both to the currently selected photo.
    """
    ctx_key  = st.session_state.get("ps_ctx_panel_key", 0)
    wkey     = f"ps_ctx_sys_type_dd_{ctx_key}"
    name_wkey = f"ps_ctx_sys_name_inp_{ctx_key}"
    sel = st.session_state.get(wkey, "")

    if not sel or sel in ("— select type —", "Custom…"):
        if sel == "— select type —":
            st.session_state.ps_ctx_sys_type = ""
        return

    old_name = st.session_state.get("ps_ctx_sys_name", "")
    all_prefixes = set(PS_SYS_PREFIX.values())

    st.session_state.ps_ctx_sys_type = sel

    # Auto-suggest prefix only if name is blank or was a previous auto-prefix
    if not old_name.strip() or old_name in all_prefixes:
        prefix = PS_SYS_PREFIX.get(sel, "")
        st.session_state.ps_ctx_sys_name = prefix
        st.session_state[name_wkey] = prefix   # update widget (safe — between runs)

    # Resolve/create stable group ID for the new (type, name) combination
    _ensure_ctx_sys_id()

    # Apply to current photo immediately
    photo, _ = _get_selected_photo()
    if photo:
        photo.system     = sel
        photo.system_id  = st.session_state.ps_ctx_sys_id
        photo.caption_id = st.session_state.get("ps_ctx_sys_name", "")
        _commit_caption(photo)


def _on_ctx_sys_name_change():
    """Fires when the system name/ID text input changes."""
    ctx_key  = st.session_state.get("ps_ctx_panel_key", 0)
    wkey     = f"ps_ctx_sys_name_inp_{ctx_key}"
    new_name = st.session_state.get(wkey, "")
    st.session_state.ps_ctx_sys_name = new_name

    # Changing the name creates a distinct group — resolve/create its ID
    _ensure_ctx_sys_id()

    photo, _ = _get_selected_photo()
    if photo:
        photo.caption_id = new_name
        photo.system_id  = st.session_state.ps_ctx_sys_id
        _commit_caption(photo)


def _on_ctx_custom_type_change():
    """Fires when the custom system type text input changes."""
    ctx_key = st.session_state.get("ps_ctx_panel_key", 0)
    wkey    = f"ps_ctx_custom_type_{ctx_key}"
    custom  = st.session_state.get(wkey, "").strip()
    st.session_state.ps_ctx_sys_type = custom
    _ensure_ctx_sys_id()

    photo, _ = _get_selected_photo()
    if photo and custom:
        photo.system     = custom
        photo.system_id  = st.session_state.ps_ctx_sys_id
        photo.caption_id = st.session_state.get("ps_ctx_sys_name", "")
        _commit_caption(photo)


# ── Per-photo caption callbacks ────────────────────────────────────────────────

def _on_view_change():
    """Fires when the user types directly into the view-type text input."""
    photo, _ = _get_selected_photo()
    if not photo:
        return
    pid = photo.photo_id
    photo.caption_view = st.session_state.get(f"ps_cv_view_{pid}", "")
    _commit_caption(photo)


def _on_note_change():
    photo, _ = _get_selected_photo()
    if not photo:
        return
    pid = photo.photo_id
    photo.caption_note = st.session_state.get(f"ps_cv_note_{pid}", "")
    _commit_caption(photo)


def _on_field_notes_change():
    photo, _ = _get_selected_photo()
    if not photo:
        return
    pid = photo.photo_id
    photo.notes = st.session_state.get(f"ps_fld_{pid}", "")
    ps_save_draft()


# ── Context helpers ────────────────────────────────────────────────────────────

def _apply_ctx_to_photo(photo):
    """
    Push the current global system context (type, name, system_id) onto a photo.
    Called before setting a view type so context is always embedded in the caption.
    No-op if the context fields are empty.
    """
    sys_type = st.session_state.get("ps_ctx_sys_type", "")
    sys_name = st.session_state.get("ps_ctx_sys_name", "")
    sys_id   = st.session_state.get("ps_ctx_sys_id", "")
    if sys_type:
        photo.system    = sys_type
        photo.system_id = sys_id or str(uuid.uuid4())[:8]
    # Always sync the name (even "" clears a stale name)
    photo.caption_id = sys_name


def _sync_ctx_from_photo(photo):
    """
    Pull a photo's system values into the global context panel so the panel
    reflects the system that the currently-selected photo belongs to.

    Only fires when the selected photo changes (guarded by ps_ctx_last_pid).
    Writes to widget state keys BEFORE they render — safe per Streamlit rules.
    Skips "Uncategorized" photos to preserve the user's active context.
    """
    if not photo or photo.system in ("", "Uncategorized"):
        return

    ctx_key   = st.session_state.get("ps_ctx_panel_key", 0)
    type_wkey = f"ps_ctx_sys_type_dd_{ctx_key}"
    name_wkey = f"ps_ctx_sys_name_inp_{ctx_key}"
    cust_wkey = f"ps_ctx_custom_type_{ctx_key}"

    sys_type = photo.system
    sys_name = photo.caption_id or ""

    # Update storage
    st.session_state.ps_ctx_sys_type = sys_type
    st.session_state.ps_ctx_sys_name = sys_name
    st.session_state.ps_ctx_sys_id   = photo.system_id or ""

    # Update widget state (safe — called before widgets render)
    if sys_type in PS_SYSTEM_TYPES:
        st.session_state[type_wkey] = sys_type
    else:
        st.session_state[type_wkey] = "Custom…"
        st.session_state[cust_wkey] = sys_type
    st.session_state[name_wkey] = sys_name


# ── System-group helpers ──────────────────────────────────────────────────────

def _ensure_ctx_sys_id() -> None:
    """
    Find or create a stable system_id UUID for (ps_ctx_sys_type, ps_ctx_sys_name).

    Searches existing photos for a matching group and reuses its ID, so that
    navigating away and back to the same system doesn't fragment the group.
    If no match is found a new UUID is generated and stored in ps_ctx_sys_id.
    Called whenever sys_type or sys_name changes.
    """
    sys_type = st.session_state.get("ps_ctx_sys_type", "")
    sys_name = st.session_state.get("ps_ctx_sys_name", "")
    if not sys_type:
        st.session_state.ps_ctx_sys_id = ""
        return
    for p in st.session_state.get("ps_photos", []):
        if p.system == sys_type and p.caption_id == sys_name and p.system_id:
            st.session_state.ps_ctx_sys_id = p.system_id
            return
    st.session_state.ps_ctx_sys_id = str(uuid.uuid4())[:8]


def _get_system_groups() -> list:
    """
    Build an ordered list of SystemGroup dicts from ps_photos.

    Groups appear in first-appearance order (upload order).
    Photos within each group are sorted by group_order.
    O(n) — safe for 100+ photos.

    Returns list of:
      {system_id, system, caption_id, photos: [PhotosheetPhoto]}
    """
    photos = st.session_state.ps_photos
    seen: dict = {}        # system_id_key -> index in groups list
    groups: list = []
    for p in photos:
        sid_key = p.system_id if p.system_id else "_uncat"
        if sid_key not in seen:
            seen[sid_key] = len(groups)
            groups.append({
                "system_id":  p.system_id or "_uncat",
                "system":     p.system,
                "caption_id": p.caption_id,
                "photos":     [],
            })
        groups[seen[sid_key]]["photos"].append(p)
    for g in groups:
        g["photos"].sort(key=lambda ph: ph.group_order)
    return groups


# ── Auto-sort ─────────────────────────────────────────────────────────────────

def _auto_sort():
    photos = st.session_state.ps_photos
    if not photos:
        return

    def sort_key(p):
        sys_pri  = PS_SYSTEM_ORDER.get(p.system, 998)
        # Secondary: keep groups with the same type together by name
        sys_name = (p.caption_id or "").lower()
        # Tertiary: view priority within group
        cap_lower = (p.caption_view or p.caption or "").lower()
        view_pri = min(
            (v for k, v in PS_VIEW_PRIORITY.items() if k.lower() in cap_lower),
            default=999,
        )
        # Quaternary: preserve original group_order within same view priority
        return (sys_pri, sys_name, view_pri, p.group_order)

    photos.sort(key=sort_key)
    _renumber(st.session_state.ps_photos)
    ps_save_draft()


# ─────────────────────────────────────────────────────────────────────────────
# PHOTOSHEET SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def _render_photosheet_sidebar():
    """
    Persistent sidebar for the Photosheet workflow.

    Upload step  — project info inputs, photo count, proceed / clear actions.
    Organize step — system group list (clickable nav), auto-sort, save draft.
    Export step  — layout picker, page count estimate.

    Common across all steps: logo, step navigation, mode switcher.
    """
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        logo = Path("assets/sterling_logo.png")
        if logo.exists():
            st.image(str(logo), use_container_width=True)
        else:
            st.markdown("**Sterling Stormwater**")

        st.markdown("---")

        step = st.session_state.get("ps_step", "upload")

        # ── Workflow label ─────────────────────────────────────────────────────
        st.markdown(
            '<p style="font-family:\'Source Code Pro\',monospace;font-size:0.65em;'
            'text-transform:uppercase;letter-spacing:2px;color:#27AD3D;margin:0 0 5px 0">'
            'Photosheet</p>',
            unsafe_allow_html=True,
        )

        # ── Step nav buttons — never disabled so styling stays consistent ────────
        step_items = [
            ("upload",   "1 · Upload"),
            ("organize", "2 · Organize"),
            ("export",   "3 · Export"),
        ]
        for step_key, step_label in step_items:
            is_active = step == step_key
            label = f"▶  {step_label}" if is_active else step_label
            if st.button(label, key=f"ps_sb_nav_{step_key}",
                         use_container_width=True):
                has_photos = bool(st.session_state.ps_photos)
                if step_key in ("organize", "export") and not has_photos:
                    st.toast("Upload photos first to access this step.", icon="⚠️")
                else:
                    if step_key == "organize" and not st.session_state.ps_selected_pid:
                        photos = st.session_state.ps_photos
                        if photos:
                            st.session_state.ps_selected_pid = photos[0].photo_id
                    if step_key in ("organize", "export"):
                        ps_sync_widget_states()
                        ps_save_draft()
                    st.session_state.ps_step = step_key
                    st.rerun()

        st.markdown("---")

        # ── Step-specific content ──────────────────────────────────────────────
        if step == "upload":
            _render_sidebar_upload()
        elif step == "organize":
            _render_sidebar_organize()
        elif step == "export":
            _render_sidebar_export()

        st.markdown("---")

        # ── Back to Home ──────────────────────────────────────────────────────
        if st.button("← Home", key="ps_sb_mode_back",
                     use_container_width=True, help="Return to Home"):
            st.session_state.current_page = "home"
            st.rerun()

        st.caption("Sterling Report Generator v1.0")


def _render_sidebar_upload():
    """Sidebar content for upload step — project info + photo stats."""
    st.markdown(
        '<p style="font-family:\'Source Code Pro\',monospace;font-size:0.65em;'
        'text-transform:uppercase;letter-spacing:2px;color:#27AD3D;margin:0 0 5px 0">'
        'Project</p>',
        unsafe_allow_html=True,
    )

    # Project info inputs.
    # Initialize widget keys from canonical storage ONCE (before widget creation).
    # Never pass value= alongside key= — that causes StreamlitAPIException on rerun.
    if "ps_sb_site" not in st.session_state:
        st.session_state.ps_sb_site = st.session_state.get("ps_site_name", "")
    if "ps_sb_date" not in st.session_state:
        st.session_state.ps_sb_date = st.session_state.get("ps_report_date", "")
    if "ps_sb_prep" not in st.session_state:
        st.session_state.ps_sb_prep = st.session_state.get("ps_prepared_by", "")

    st.text_input("Site Name",    key="ps_sb_site", placeholder="Riverside Commons")
    st.text_input("Report Date",  key="ps_sb_date", placeholder="April 10, 2026")
    st.text_input("Prepared By",  key="ps_sb_prep", placeholder="J. Smith")

    # Sync canonical keys after widget renders (reading widget state is always safe)
    st.session_state.ps_site_name  = st.session_state.ps_sb_site
    st.session_state.ps_report_date = st.session_state.ps_sb_date
    st.session_state.ps_prepared_by = st.session_state.ps_sb_prep

    st.markdown("---")

    # Photo stats + actions
    n = len(st.session_state.ps_photos)
    if n > 0:
        st.markdown(
            f'<div style="font-size:0.85em;color:#b8c4c2;margin-bottom:8px">'
            f'<b style="color:#ffffff">{n}</b> photo(s) queued</div>',
            unsafe_allow_html=True,
        )
        if st.button(f"Organize {n} →", type="primary",
                     key="ps_sb_go_organize", use_container_width=True):
            if not st.session_state.ps_selected_pid and st.session_state.ps_photos:
                st.session_state.ps_selected_pid = st.session_state.ps_photos[0].photo_id
            st.session_state.ps_step = "organize"
            st.rerun()
        if st.button("🗑 Clear All", key="ps_sb_clear_all", use_container_width=True):
            st.session_state.ps_photos = []
            st.session_state.ps_photo_bytes = {}
            st.session_state.ps_thumb_bytes = {}
            st.session_state.ps_selected_pid = ""
            ps_save_draft()
            st.rerun()
    else:
        st.markdown(
            '<span style="color:#5c6c75;font-size:0.82em">No photos yet — '
            'upload below</span>',
            unsafe_allow_html=True,
        )


def _render_sidebar_organize():
    """Sidebar content for organize step — system groups + actions."""
    photos = st.session_state.ps_photos
    n = len(photos)
    n_groups = len(set((p.system_id or "_uncat") for p in photos))

    # Stats
    st.markdown(
        f'<div style="font-size:0.82em;color:#b8c4c2;margin-bottom:8px">'
        f'<b style="color:#fff">{n}</b> photos · '
        f'<b style="color:#fff">{n_groups}</b> group(s)</div>',
        unsafe_allow_html=True,
    )

    # Quick actions
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔀 Sort", key="ps_sb_autosort", use_container_width=True,
                     help="Auto-sort by stormwater flow priority"):
            _auto_sort()
            st.rerun()
    with c2:
        if st.button("💾 Save", key="ps_sb_save_draft", use_container_width=True,
                     help="Save draft to disk"):
            ps_save_draft()
            st.toast("Draft saved", icon="✅")

    st.markdown("---")

    if st.button("Export →", type="primary", key="ps_sb_go_export",
                 use_container_width=True):
        ps_sync_widget_states()
        ps_save_draft()
        st.session_state.ps_step = "export"
        st.rerun()

    st.markdown("---")

    # System groups — clickable navigation
    st.markdown(
        '<p style="font-family:\'Source Code Pro\',monospace;font-size:0.65em;'
        'text-transform:uppercase;letter-spacing:2px;color:#27AD3D;margin:0 0 5px 0">'
        'Systems</p>',
        unsafe_allow_html=True,
    )

    groups = _get_system_groups()
    if not groups:
        st.markdown(
            '<span style="color:#5c6c75;font-size:0.80em">No groups yet — '
            'assign a system to photos</span>',
            unsafe_allow_html=True,
        )
    else:
        selected_pid = st.session_state.get("ps_selected_pid", "")
        for g in groups:
            sys_label = g["caption_id"] or g["system"] or "Uncategorized"
            n_in_group = len(g["photos"])
            is_active = any(p.photo_id == selected_pid for p in g["photos"])

            # Show system type as a tiny tag above each group button
            if g["system"] and g["system"] != "Uncategorized":
                st.markdown(
                    f'<div style="font-size:0.72em;color:#ffffff;'
                    f'text-transform:uppercase;letter-spacing:1px;'
                    f'margin:4px 0 1px 4px">{g["system"]}</div>',
                    unsafe_allow_html=True,
                )
            btn_label = (f"▶  {sys_label}  ({n_in_group})"
                         if is_active else f"{sys_label}  ({n_in_group})")
            if st.button(btn_label, key=f"ps_sb_grp_{g['system_id']}",
                         use_container_width=True):
                # Jump to first photo in group
                first = g["photos"][0]
                st.session_state.ps_selected_pid = first.photo_id
                st.rerun()


def _render_sidebar_export():
    """Sidebar content for export step — layout picker + stats."""
    photos = st.session_state.ps_photos
    n = len(photos)

    # Layout selector
    st.markdown(
        '<p style="font-family:\'Source Code Pro\',monospace;font-size:0.65em;'
        'text-transform:uppercase;letter-spacing:2px;color:#27AD3D;margin:0 0 5px 0">'
        'Layout</p>',
        unsafe_allow_html=True,
    )

    layout_keys = list(PS_LAYOUTS.keys())
    layout_labels = {
        "3x2": "3×2 · 6/page",
        "3x3": "3×3 · 9/page",
        "2x2": "2×2 · 4/page",
        "full_page": "Full · 1/page",
    }

    cur_layout = st.session_state.get("ps_layout", "3x2")
    if cur_layout not in layout_keys:
        cur_layout = "3x2"

    sel = st.radio(
        "layout_radio",
        layout_keys,
        index=layout_keys.index(cur_layout),
        format_func=lambda k: layout_labels.get(k, k),
        key="ps_sb_layout_radio",
        label_visibility="collapsed",
    )
    if sel != st.session_state.get("ps_layout"):
        st.session_state.ps_layout = sel

    st.markdown("---")

    # Page count estimate
    import math
    per_page = PS_LAYOUTS.get(sel, {}).get("per_page", 6)
    n_pages = math.ceil(n / per_page) if per_page else 1
    st.markdown(
        f'<div style="font-size:0.82em;color:#b8c4c2;margin-bottom:8px">'
        f'<b style="color:#fff">{n}</b> photos · '
        f'<b style="color:#fff">~{n_pages}</b> page(s)</div>',
        unsafe_allow_html=True,
    )

    if st.button("← Organize", key="ps_sb_back_organize",
                 use_container_width=True):
        st.session_state.ps_step = "organize"
        st.rerun()


# ── Step indicator ──────────────────────────────────────────────────────────────

def _render_step_indicator(current_step: str):
    """Minimal step indicator bar — complements the sidebar step nav."""
    step_labels = {
        "upload":   "1 · Upload",
        "organize": "2 · Organize",
        "export":   "3 · Export",
    }
    label = step_labels.get(current_step, current_step)
    st.markdown(
        f'<div style="background:#001e2b;padding:6px 14px;'
        f'border-bottom:2px solid #27AD3D;margin-bottom:8px;border-radius:4px;">'
        f'<span style="font-family:\'Source Code Pro\',monospace;font-size:0.65em;'
        f'text-transform:uppercase;letter-spacing:2px;color:#27AD3D">Photosheet</span>'
        f'&nbsp;&nbsp;<span style="color:#ffffff;font-size:0.82em;font-weight:500">'
        f'{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def _render_upload():
    st.markdown(
        '<h3 style="color:#ffffff;margin:0 0 8px 0;font-size:1.1em">📁 Upload Photos</h3>',
        unsafe_allow_html=True,
    )

    # ── Active System — set BEFORE uploading so photos inherit it ────────────
    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:4px 0 4px">Active System</div>',
        unsafe_allow_html=True,
    )
    _render_system_context(None)

    # Draft restore
    if not st.session_state.ps_photos:
        draft_path = ps_find_latest_draft()
        if draft_path:
            st.info("A previous photosheet draft was found. Restore it?", icon="💾")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("✅ Restore Draft", key="ps_restore_draft"):
                    if ps_load_draft(draft_path):
                        st.success("Draft restored.")
                        st.rerun()
                    else:
                        st.error("Could not read draft file.")
            with rc2:
                if st.button("🗑 Start Fresh", key="ps_discard_draft"):
                    try:
                        Path(draft_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                    st.rerun()
            st.markdown("---")

    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:10px 0 4px">Upload</div>',
        unsafe_allow_html=True,
    )
    # Key-bumped so the widget resets (clears selected files) after each batch
    uploader_key = f"ps_uploader_{st.session_state.ps_uploader_key}"
    uploaded_files = st.file_uploader(
        "Drop photos here or click to browse",
        type=["jpg", "jpeg", "png", "heic", "heif"],
        accept_multiple_files=True,
        key=uploader_key,
    )

    if uploaded_files:
        existing  = {p.filename for p in st.session_state.ps_photos}
        new_files = [uf for uf in uploaded_files
                     if Path(uf.name).suffix.lower() in _IMAGE_EXTS
                     and uf.name not in existing]
        bad_files = [uf for uf in uploaded_files
                     if Path(uf.name).suffix.lower() not in _IMAGE_EXTS]
        dupes     = [uf for uf in uploaded_files
                     if uf.name in existing
                     and Path(uf.name).suffix.lower() in _IMAGE_EXTS]

        if bad_files:
            st.warning(f"**{len(bad_files)} non-image file(s) skipped:** " +
                       ", ".join(f.name for f in bad_files), icon="⚠️")
        if dupes:
            st.info(f"**{len(dupes)} duplicate(s) skipped:** " +
                    ", ".join(f.name for f in dupes), icon="ℹ️")

        if new_files:
            # Auto-process immediately — no extra button click needed
            with st.spinner(f"Processing {len(new_files)} photo(s)…"):
                _add_photos(new_files)
            ps_save_draft()
            # Bump key so the file uploader widget resets (shows empty/ready)
            st.session_state.ps_uploader_key += 1
            st.rerun()

    photos = st.session_state.ps_photos
    if photos:
        n = len(photos)
        st.markdown(
            f'<div style="font-size:0.80em;color:#b8c4c2;margin:6px 0 4px">'
            f'<b style="color:#fff">{n}</b> photo(s) queued</div>',
            unsafe_allow_html=True,
        )
        # Compact scrollable list — dark theme
        rows = "".join(
            f'<div style="padding:3px 0;font-size:0.85em;'
            f'border-bottom:1px solid #3d4f58">'
            f'<span style="color:#27AD3D;font-weight:bold">#{p.order}</span>'
            f'&nbsp;&nbsp;<span style="color:#b8c4c2">{p.filename}</span></div>'
            for p in photos
        )
        st.markdown(
            f'<div style="max-height:260px;overflow-y:auto;border:1px solid #3d4f58;'
            f'background:#152e3e;border-radius:6px;padding:6px 10px">{rows}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        col_clear, col_go = st.columns([1, 2])
        with col_clear:
            if st.button("🗑 Clear All", key="ps_clear_all"):
                st.session_state.ps_photos = []
                st.session_state.ps_photo_bytes = {}
                st.session_state.ps_thumb_bytes = {}
                st.session_state.ps_selected_pid = ""
                ps_save_draft()
                st.rerun()
        with col_go:
            if st.button(f"Organize {n} Photos →", type="primary",
                         key="ps_go_organize", use_container_width=True):
                if not st.session_state.ps_selected_pid and photos:
                    st.session_state.ps_selected_pid = photos[0].photo_id
                st.session_state.ps_step = "organize"
                st.rerun()
    else:
        st.markdown(
            '<div style="background:#152e3e;border:2px dashed #3d4f58;border-radius:8px;'
            'padding:28px;text-align:center;color:#5c6c75">'
            '<div style="font-size:2em">📷</div>'
            '<p style="margin:4px 0 0">No photos uploaded yet.</p></div>',
            unsafe_allow_html=True,
        )


def _add_photos(files):
    project_id = st.session_state.ps_project_id
    photo_dir = Path("projects") / project_id / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)

    # ── Capture active system context at upload time ───────────────────────────
    ctx_sys_type = st.session_state.get("ps_ctx_sys_type", "")
    ctx_sys_name = st.session_state.get("ps_ctx_sys_name", "")
    ctx_sys_id   = st.session_state.get("ps_ctx_sys_id", "")

    # If a system type is active but no group ID yet, generate one now
    if ctx_sys_type and not ctx_sys_id:
        ctx_sys_id = str(uuid.uuid4())[:8]
        st.session_state.ps_ctx_sys_id = ctx_sys_id

    # Determine the system_id to assign (empty string for uncategorized)
    assign_sys_id = ctx_sys_id if ctx_sys_type else "_uncat"

    # Compute starting group_order for this batch within the target group
    existing_in_group = sum(
        1 for p in st.session_state.ps_photos
        if (p.system_id or "_uncat") == assign_sys_id
    )

    heic_errors = []
    start_order = len(st.session_state.ps_photos) + 1

    for i, uf in enumerate(files):
        try:
            ext = Path(uf.name).suffix.lower()
            if ext in (".heic", ".heif"):
                try:
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                except ImportError:
                    heic_errors.append(uf.name)
                    continue

            uf.seek(0)
            raw = uf.read()
            img = Image.open(io.BytesIO(raw))
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            stem = Path(uf.name).stem
            dest = photo_dir / f"{stem}.jpg"
            counter = 1
            while dest.exists():
                dest = photo_dir / f"{stem}_{counter}.jpg"
                counter += 1

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            full_bytes = buf.getvalue()
            dest.write_bytes(full_bytes)

            photo = PhotosheetPhoto(
                photo_id=str(uuid.uuid4())[:8],
                filename=uf.name,
                filepath=str(dest.resolve()),
                system=ctx_sys_type or "Uncategorized",
                caption_id=ctx_sys_name,
                system_id=assign_sys_id,
                order=start_order + i,
                group_order=existing_in_group + i + 1,
            )
            st.session_state.ps_photos.append(photo)
            st.session_state.ps_photo_bytes[photo.photo_id] = full_bytes
            st.session_state.ps_thumb_bytes[photo.photo_id] = _make_thumb(full_bytes)

        except Exception as exc:
            st.error(f"Could not process **{uf.name}**: {exc}")

    if heic_errors:
        st.warning("**HEIC photos skipped** — install `pillow-heif` to enable iPhone support.",
                   icon="📷")

    _renumber(st.session_state.ps_photos)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — ORGANIZE
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_thumbnails():
    """
    Regenerate any missing thumbnails from disk.
    Needed when photos are loaded from a saved draft (ps_thumb_bytes is not
    persisted to disk — only the filepath is).
    """
    for p in st.session_state.ps_photos:
        if p.photo_id not in st.session_state.ps_thumb_bytes:
            fp = Path(p.filepath)
            if fp.exists():
                try:
                    raw = fp.read_bytes()
                    st.session_state.ps_thumb_bytes[p.photo_id] = _make_thumb(raw)
                    # Also cache full-res while we're reading
                    if p.photo_id not in st.session_state.ps_photo_bytes:
                        st.session_state.ps_photo_bytes[p.photo_id] = raw
                except Exception:
                    pass


# ── Feature → conditional issue-tag mapping ──────────────────────────────────
# Keys are lower-case substrings matched against caption_view.
# Longest key wins (so "inlet area" beats "inlet").
_FEATURE_ISSUES: dict[str, list[str]] = {
    "inlet area":  ['>4" Sediment', 'Partially Obstructed', 'Fully Obstructed', 'Debris Present'],
    "inlet":       ['>4" Sediment', 'Partially Obstructed', 'Fully Obstructed', 'Debris Present'],
    "outlet":      ['Partially Obstructed', 'Fully Obstructed', 'Erosion Present', 'Structural Damage'],
    "inside":      ['>4" Sediment', 'Sheen on Water', 'Debris Present', 'Structural Damage', 'Missing Hardware'],
    "surface":     ['>4" Sediment', 'Excess Vegetation', 'Standing Water', 'Erosion Present', 'Debris Present'],
    "overall":     ['Erosion Present', 'Excess Vegetation', 'Debris Present', 'Structural Damage', 'Animal Burrow'],
    "maintenance": ['Debris Present', 'Excess Vegetation', 'Standing Water', '>4" Sediment'],
    "pipe":        ['Partially Obstructed', 'Fully Obstructed', 'Structural Damage', 'Detached Hood'],
}


def _get_relevant_issues(caption_view: str) -> list[str]:
    """
    Return the PS_ISSUE_TAGS subset relevant to the active feature keyword.
    Checks longest keys first; falls back to the full list when no match.
    """
    cv_lower = (caption_view or "").lower()
    for keyword in sorted(_FEATURE_ISSUES, key=len, reverse=True):
        if keyword in cv_lower:
            return _FEATURE_ISSUES[keyword]
    return PS_ISSUE_TAGS


def _parse_smart_input(raw: str, sections: dict) -> str:
    """
    Normalize free-text view input against the token taxonomy.

    Algorithm:
      1. Build a lookup: token_lower → (section_key, canonical_form).
      2. Greedy left-to-right scan — try the longest phrase match per position.
      3. Collect one canonical token per section (first match wins).
      4. Reconstruct in section order: view_prefix → features → numbers,
         then append any unrecognized words verbatim.

    Examples:
      "inlet view 1"     → "View Inlet 1"
      "view of inlet 1"  → "View of Inlet 1"
      "pipe inside"      → "Inside Pipe"
      "cracked frame"    → "cracked frame"   (passthrough — no token match)
    """
    if not raw.strip():
        return ""

    lookup: dict[str, tuple[str, str]] = {}
    for sec_key, (_, tokens) in sections.items():
        for tok in tokens:
            lookup[tok.lower()] = (sec_key, tok)

    words = raw.split()
    result_by_sec: dict[str, str] = {}
    leftover: list[str] = []
    i = 0
    while i < len(words):
        matched = False
        for length in range(min(4, len(words) - i), 0, -1):
            phrase = " ".join(words[i : i + length]).lower()
            if phrase in lookup:
                sec_key, canonical = lookup[phrase]
                if sec_key not in result_by_sec:   # first match per section wins
                    result_by_sec[sec_key] = canonical
                i += length
                matched = True
                break
        if not matched:
            leftover.append(words[i])
            i += 1

    parts = [
        result_by_sec[k]
        for k in ["view_prefix", "features", "numbers"]
        if k in result_by_sec
    ]
    parts.extend(leftover)
    return " ".join(parts)


def _on_smart_view_change():
    """
    on_change callback for the smart view-type text input.
    Parses raw text through _parse_smart_input, commits to photo,
    and propagates to all group members when batch mode is active.
    """
    photo, _ = _get_selected_photo()
    if not photo:
        return
    pid = photo.photo_id
    raw = st.session_state.get(f"ps_cv_view_{pid}", "")
    sections = st.session_state.get("ps_quick_sections", {})
    parsed = _parse_smart_input(raw, sections)
    _apply_ctx_to_photo(photo)
    photo.caption_view = parsed
    _commit_caption(photo)
    if st.session_state.get("ps_batch_apply", False):
        sid = photo.system_id or "_uncat"
        for p in st.session_state.ps_photos:
            if (p.system_id or "_uncat") == sid and p.photo_id != pid:
                p.caption_view = parsed
                _commit_caption(p)


def _render_smart_view_input(active_photo) -> None:
    """
    Smart view-type builder: single text input + chip suggestion rows.

    ┌─ VIEW TYPE ──────────────────────────────────────────────────────────┐
    │  [text: "e.g. View Inlet 1"]                          [⌫]  [✕]     │
    │  View:    [View] [View of] [Surface View] [Inside View]              │
    │  Feature: [Inlet] [Outlet] [Inlet Area] [Inside] [Surface] …        │
    │  #:       [1] [2] [3] [4]                                            │
    │  ▸ Edit token buttons (expander)                                     │
    └─────────────────────────────────────────────────────────────────────┘

    Typing "inlet view 1" + Enter normalizes to "View Inlet 1".
    Chip buttons append a single token to whatever is already in the field.
    Batch-apply toggle propagates the change to every photo in the group.
    """
    pid      = active_photo.photo_id
    sections = st.session_state.ps_quick_sections
    cur      = active_photo.caption_view
    _stg_key = f"ps_cv_view_{pid}_stg"  # staging key — applied BEFORE widget renders

    def _chip_append(tok: str):
        """Append tok to current view, commit, and batch-apply if toggled."""
        _apply_ctx_to_photo(active_photo)
        nv = (cur + " " + tok).strip() if cur else tok
        active_photo.caption_view = nv
        # Write to staging key, NOT the widget key — widget already rendered this run
        st.session_state[_stg_key] = nv
        _commit_caption(active_photo)
        if st.session_state.get("ps_batch_apply", False):
            sid = active_photo.system_id or "_uncat"
            for p in st.session_state.ps_photos:
                if (p.system_id or "_uncat") == sid and p.photo_id != pid:
                    p.caption_view = nv
                    _commit_caption(p)

    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:6px 0 3px">View Type</div>',
        unsafe_allow_html=True,
    )

    # ── Apply any staged view value BEFORE the text_input renders ────────────
    if _stg_key in st.session_state:
        st.session_state[f"ps_cv_view_{pid}"] = st.session_state.pop(_stg_key)

    # ── Smart text input + ⌫ / ✕ ─────────────────────────────────────────────
    inp_col, back_col, clr_col = st.columns([6, 1, 1])
    with inp_col:
        st.text_input(
            "view_smart",
            value=active_photo.caption_view,
            key=f"ps_cv_view_{pid}",
            on_change=_on_smart_view_change,
            placeholder='Type e.g. "View Inlet 1" — auto-normalizes on Enter',
            label_visibility="collapsed",
        )
    with back_col:
        if st.button("⌫", key=f"ps_sv_back_{pid}", use_container_width=True,
                     help="Remove last word"):
            nv = cur.rsplit(" ", 1)[0] if " " in cur else ""
            active_photo.caption_view = nv
            st.session_state[_stg_key] = nv
            _commit_caption(active_photo)
            if st.session_state.get("ps_batch_apply", False):
                sid = active_photo.system_id or "_uncat"
                for p in st.session_state.ps_photos:
                    if (p.system_id or "_uncat") == sid and p.photo_id != pid:
                        p.caption_view = nv
                        _commit_caption(p)
            st.rerun()
    with clr_col:
        if st.button("✕", key=f"ps_sv_clr_{pid}", use_container_width=True,
                     help="Clear view type"):
            active_photo.caption_view = ""
            st.session_state[_stg_key] = ""
            _commit_caption(active_photo)
            if st.session_state.get("ps_batch_apply", False):
                sid = active_photo.system_id or "_uncat"
                for p in st.session_state.ps_photos:
                    if (p.system_id or "_uncat") == sid and p.photo_id != pid:
                        p.caption_view = ""
                        _commit_caption(p)
            st.rerun()

    # ── Chip rows — one section per row ──────────────────────────────────────
    for sec_key, (sec_label, tokens) in sections.items():
        if not tokens:
            continue
        lc, *bcols = st.columns([0.55] + [1] * min(len(tokens), 6))
        with lc:
            st.markdown(
                f'<span style="font-size:0.60em;color:#5c6c75;white-space:nowrap;'
                f'display:block;text-align:right;padding-top:5px">{sec_label}</span>',
                unsafe_allow_html=True,
            )
        for ci, tok in enumerate(tokens[:6]):
            with bcols[ci]:
                if st.button(tok, key=f"ps_chip_{pid}_{sec_key}_{ci}",
                             use_container_width=True):
                    _chip_append(tok)
                    st.rerun()

    # ── Token editor ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Edit token buttons", expanded=False):
        st.markdown(
            '<div style="font-size:0.82em;color:#b8c4c2;margin-bottom:6px">'
            'One token per line per section. Reorder or rename freely, '
            'then click <b style="color:#fff">Save</b>.</div>',
            unsafe_allow_html=True,
        )
        edited: dict[str, list[str]] = {}
        for sec_key, (sec_label, tokens) in sections.items():
            edited_text = st.text_area(
                sec_label,
                value="\n".join(tokens),
                height=80,
                key=f"ps_tok_edit_{sec_key}",
            )
            edited[sec_key] = [t.strip() for t in edited_text.splitlines() if t.strip()]

        na1, na2, na3 = st.columns([2, 2, 1])
        with na1:
            add_sec = st.selectbox(
                "Section",
                list(sections.keys()),
                format_func=lambda k: sections[k][0],
                key="ps_tok_add_sec",
                label_visibility="collapsed",
            )
        with na2:
            add_val = st.text_input(
                "Token value",
                key="ps_tok_add_val",
                placeholder='e.g. "Forebay"',
                label_visibility="collapsed",
            )
        with na3:
            if st.button("+ Add", key="ps_tok_do_add", use_container_width=True):
                t = (add_val or "").strip()
                cur_toks = edited.get(add_sec, list(sections[add_sec][1]))
                if t and t not in cur_toks:
                    edited[add_sec] = cur_toks + [t]

        ec1, ec2 = st.columns(2)
        with ec1:
            if st.button("💾 Save", key="ps_tokens_save",
                         use_container_width=True, type="primary"):
                new_secs = {
                    k: (sections[k][0], edited.get(k, list(sections[k][1])))
                    for k in sections
                }
                st.session_state.ps_quick_sections = new_secs
                _save_sections(new_secs)
                st.success("Saved.", icon="✅")
                st.rerun()
        with ec2:
            if st.button("↺ Defaults", key="ps_tokens_reset", use_container_width=True):
                defaults = {k: (lbl, list(toks))
                            for k, (lbl, toks) in _DEFAULT_SECTIONS.items()}
                st.session_state.ps_quick_sections = defaults
                _save_sections(defaults)
                st.rerun()


def _render_field_notes(active_photo) -> None:
    """
    Field notes quick-entry panel.  Two compact rows of buttons + a textarea.

    ┌─ FIELD NOTES ─────────────────────────────────────────────────────────┐
    │  Severity  [Minimal] [Light] [Moderate] [Heavy] [Significant] [Excess]│
    │  Issues    [>4" Sediment] [Sheen] [Obstructed] … (4 per row)          │
    │  [textarea — full notes text]                 [✕ Clear notes]         │
    └───────────────────────────────────────────────────────────────────────┘

    Severity buttons append "<word> " as a leading modifier; issue buttons
    append the full phrase.  Either way the textarea is always editable.
    Notes appear on the notes page of the DOCX — NOT in the caption.
    """
    pid = active_photo.photo_id

    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:4px 0 4px">Field Notes</div>',
        unsafe_allow_html=True,
    )

    def _append_note(text: str):
        existing = active_photo.notes.rstrip()
        sep = ", " if existing else ""
        active_photo.notes = existing + sep + text
        st.session_state[f"ps_fld_{pid}"] = active_photo.notes
        ps_save_draft()

    # ── Row 1: Severity ───────────────────────────────────────────────────────
    sv_lc, *sv_bcols = st.columns([0.7] + [1] * len(PS_SEVERITY_TAGS))
    with sv_lc:
        st.markdown(
            '<div style="font-size:0.65em;color:#5c6c75;text-align:right;'
            'padding-top:6px;padding-right:3px;white-space:nowrap">Severity</div>',
            unsafe_allow_html=True,
        )
    for si, sev in enumerate(PS_SEVERITY_TAGS):
        with sv_bcols[si]:
            if st.button(sev, key=f"ps_sev_{pid}_{si}", use_container_width=True):
                _append_note(sev)
                st.rerun()

    # ── Row 2+: Conditional issues (filtered by active feature keyword) ──────
    relevant_issues = _get_relevant_issues(active_photo.caption_view)
    ISSUE_COLS = 4
    for row_start in range(0, len(relevant_issues), ISSUE_COLS):
        chunk = relevant_issues[row_start : row_start + ISSUE_COLS]
        label_html = (
            '<div style="font-size:0.65em;color:#5c6c75;text-align:right;'
            'padding-top:6px;padding-right:3px;white-space:nowrap">'
            + ("Issues" if row_start == 0 else "") + "</div>"
        )
        iss_lc, *iss_bcols = st.columns([0.7] + [1] * ISSUE_COLS)
        with iss_lc:
            st.markdown(label_html, unsafe_allow_html=True)
        for ci, tag in enumerate(chunk):
            with iss_bcols[ci]:
                if st.button(tag, key=f"ps_tag_{pid}_{row_start}_{ci}",
                             use_container_width=True):
                    _append_note(tag)
                    st.rerun()

    # ── Textarea + Clear ──────────────────────────────────────────────────────
    _fld_stg = f"ps_fld_{pid}_stg"
    # Apply any staged notes value BEFORE textarea registers its key
    if _fld_stg in st.session_state:
        st.session_state[f"ps_fld_{pid}"] = st.session_state.pop(_fld_stg)

    ta_col, clr_col = st.columns([6, 1])
    with ta_col:
        st.text_area(
            "Notes",
            value=active_photo.notes,
            key=f"ps_fld_{pid}",
            on_change=_on_field_notes_change,
            height=64,
            placeholder="Tap above or type…",
            label_visibility="collapsed",
        )
    with clr_col:
        st.markdown('<div style="padding-top:2px">', unsafe_allow_html=True)
        if st.button("✕", key=f"ps_fld_clr_{pid}", use_container_width=True,
                     help="Clear notes"):
            active_photo.notes = ""
            st.session_state[_fld_stg] = ""  # stage — textarea already rendered
            ps_save_draft()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _render_system_context(active_photo):
    """
    Render the persistent system context panel at the top of the caption builder.

    Layout (top-to-bottom in script = render order):
      ① Header row: label  |  [✕ Clear] button   ← Clear rendered FIRST
      ② Input row:  [System Type ▾]  |  [Name]
      ③ Custom type input (only if "Custom…" selected)
      ④ Status badge

    The Clear button appears before the inputs in script execution order.
    When clicked it calls st.rerun() immediately, which stops execution before
    the inputs render — so writing to their widget keys is safe (Streamlit
    prohibits writing to a key only AFTER that widget renders in the same run).
    """
    ctx_type = st.session_state.get("ps_ctx_sys_type", "")
    ctx_name = st.session_state.get("ps_ctx_sys_name", "")
    ctx_key  = st.session_state.get("ps_ctx_panel_key", 0)

    type_wkey = f"ps_ctx_sys_type_dd_{ctx_key}"
    name_wkey = f"ps_ctx_sys_name_inp_{ctx_key}"
    cust_wkey = f"ps_ctx_custom_type_{ctx_key}"

    # ── Card shell ────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#1a2d4a;border:1px solid #2d4f6e;border-radius:7px;'
        'padding:7px 10px 7px;margin-bottom:6px">',
        unsafe_allow_html=True,
    )

    # ── ① Header + Clear (Clear must render BEFORE the inputs) ───────────────
    hc1, hc2 = st.columns([5, 1])
    with hc1:
        st.markdown(
            '<div style="font-size:0.68em;text-transform:uppercase;letter-spacing:0.09em;'
            'color:#8094D4;font-weight:700;padding-top:2px">◈ Current System</div>',
            unsafe_allow_html=True,
        )
    with hc2:
        if st.button("✕ Clear", key="ps_ctx_clear", use_container_width=True,
                     help="Clear system context — existing photo captions are preserved"):
            st.session_state.ps_ctx_sys_type = ""
            st.session_state.ps_ctx_sys_name = ""
            # Write to widget states — safe because st.rerun() fires before inputs render
            st.session_state[name_wkey] = ""
            st.session_state.pop(type_wkey, None)   # delete so selectbox resets to index 0
            st.session_state.pop(cust_wkey, None)
            # Bump panel key so all context widgets get fresh keys next render
            st.session_state.ps_ctx_panel_key = ctx_key + 1
            st.rerun()

    # ── ② Input row ──────────────────────────────────────────────────────────
    _ctx_opts = ["— select type —"] + PS_SYSTEM_TYPES + ["Custom…"]

    # Compute selectbox index from stored type
    if ctx_type in PS_SYSTEM_TYPES:
        ctx_type_idx = PS_SYSTEM_TYPES.index(ctx_type) + 1  # +1 for "— select type —"
    elif ctx_type:                                            # custom type stored
        ctx_type_idx = len(_ctx_opts) - 1                    # → "Custom…"
    else:
        ctx_type_idx = 0                                      # → "— select type —"

    ic1, ic2 = st.columns([3, 2])
    with ic1:
        st.selectbox(
            "System Type",
            _ctx_opts,
            index=ctx_type_idx,
            key=type_wkey,
            on_change=_on_ctx_sys_type_change,
            label_visibility="collapsed",
        )
    with ic2:
        st.text_input(
            "System Name / ID",
            value=ctx_name,
            key=name_wkey,
            on_change=_on_ctx_sys_name_change,
            placeholder="e.g. USF-1",
            label_visibility="collapsed",
        )

    # ── ③ Custom type input (shown only when "Custom…" selected) ─────────────
    if st.session_state.get(type_wkey) == "Custom…":
        custom_default = ctx_type if ctx_type not in PS_SYSTEM_TYPES else ""
        st.text_input(
            "Custom system type",
            value=custom_default,
            key=cust_wkey,
            on_change=_on_ctx_custom_type_change,
            placeholder="e.g. Gravel Wetland, Bioswale, Custom BMP",
        )

    # ── ④ Status badge ────────────────────────────────────────────────────────
    # Derive display type: prefer custom input over stored type for live preview
    display_type = ctx_type
    if st.session_state.get(type_wkey) == "Custom…":
        display_type = st.session_state.get(cust_wkey, ctx_type) or ctx_type

    badge_parts = [p for p in [display_type, ctx_name] if p]
    if badge_parts:
        badge_html = " <span style='color:#5c6c75'>–</span> ".join(badge_parts)
        st.markdown(
            f'<div style="font-size:0.82em;color:#b8c4c2;margin-top:5px">'
            f'<span style="font-weight:700;color:#27AD3D">✦</span>&nbsp;{badge_html}'
            f'<span style="color:#5c6c75;font-size:0.88em;margin-left:8px">'
            f'· auto-applied to each photo</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:0.8em;color:#5c6c75;margin-top:4px;font-style:italic">'
            'No system selected — only view type will appear in caption</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_organize():
    photos = st.session_state.ps_photos
    n = len(photos)

    if not photos:
        st.warning("No photos to organize. Go back and upload photos first.", icon="⚠️")
        if st.button("← Back to Upload"):
            st.session_state.ps_step = "upload"
            st.rerun()
        return

    # Lazy-load quick-view tokens (first organize render, or after session reset)
    _ensure_tokens()

    # Regenerate any thumbnails missing from cache (e.g. after draft restore)
    _ensure_thumbnails()

    # Ensure selection is valid
    active_photo, active_idx = _get_selected_photo()

    # ── Sync context panel from newly-selected photo ──────────────────────────
    # Runs BEFORE any widget renders so writing to widget state keys is safe.
    # Only triggers when the selected photo actually changes (not on every rerun).
    last_pid = st.session_state.get("ps_ctx_last_pid", "")
    if active_photo and active_photo.photo_id != last_pid:
        st.session_state.ps_ctx_last_pid = active_photo.photo_id
        _sync_ctx_from_photo(active_photo)

    # ── Nav bar — compact, sidebar handles auto-sort ──────────────────────────
    nc1, nc2, nc3 = st.columns([1, 4, 1])
    with nc1:
        if st.button("← Upload", key="org_back", use_container_width=True):
            st.session_state.ps_step = "upload"
            st.rerun()
    with nc2:
        n_groups = len(set((p.system_id or "_uncat") for p in photos))
        pid_str = f"#{active_photo.order}" if active_photo else "—"
        st.markdown(
            f'<div style="text-align:center;padding-top:5px;font-size:0.82em;color:#b8c4c2">'
            f'<b style="color:#fff">{n}</b> photos · '
            f'<b style="color:#fff">{n_groups}</b> group(s) · '
            f'<span style="color:#27AD3D">{pid_str}</span> selected</div>',
            unsafe_allow_html=True,
        )
    with nc3:
        if st.button("Export →", type="primary", key="org_next", use_container_width=True):
            ps_sync_widget_states()
            ps_save_draft()
            st.session_state.ps_step = "export"
            st.rerun()

    # ── Compact button + chip style — dark theme, scoped to organize step ────
    st.markdown("""
<style>
/* ── Image preview: compact height, dark bg ── */
section[data-testid="stMain"] [data-testid="stImage"] {
    text-align: center;
}
section[data-testid="stMain"] [data-testid="stImage"] img {
    max-height: 210px !important;
    width: 100% !important;
    object-fit: contain !important;
    background: #152e3e;
    border-radius: 4px;
    display: block;
}

/* ── Tighten horizontal dividers ── */
section[data-testid="stMain"] hr {
    margin: 4px 0 !important;
}

/* ── Secondary (chip) buttons: dark style, high-contrast text ── */
section[data-testid="stMain"] button[kind="secondary"] {
    padding: 2px 8px !important;
    font-size: 0.70rem !important;
    min-height: 24px !important;
    line-height: 1.2 !important;
    font-weight: 500 !important;
    background-color: #1c2d38 !important;
    border: 1px solid #3d4f58 !important;
    color: #e8edeb !important;
    border-radius: 12px !important;
    transition: background 0.1s, border-color 0.1s !important;
}
section[data-testid="stMain"] button[kind="secondary"]:hover {
    background-color: #1eaedb !important;
    border-color: #1eaedb !important;
    color: #ffffff !important;
}
section[data-testid="stMain"] button[kind="secondary"]:active {
    background-color: #178cae !important;
}

/* ── Primary buttons: compact ── */
section[data-testid="stMain"] button[kind="primary"] {
    padding: 4px 10px !important;
    font-size: 0.71rem !important;
    min-height: 26px !important;
    line-height: 1.2 !important;
    font-weight: 600 !important;
}

/* ── Tighter text inputs ── */
section[data-testid="stMain"] .stTextInput input,
section[data-testid="stMain"] .stTextArea textarea {
    font-size: 0.82rem !important;
    padding: 4px 8px !important;
}
section[data-testid="stMain"] label[data-testid="stWidgetLabel"] p {
    font-size: 0.78rem !important;
}

/* ── Tighter column gaps for dense button grids ── */
section[data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    gap: 4px !important;
}

/* ── Reduce block container vertical padding ── */
section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] > div {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
</style>
""", unsafe_allow_html=True)

    if not active_photo:
        st.markdown(
            '<div style="color:#5c6c75;padding:40px;text-align:center">'
            'Select a photo to begin</div>',
            unsafe_allow_html=True,
        )
        return

    pid = active_photo.photo_id

    # ── Two-pane inspector: [filmstrip + preview | Photo Inspector] ───────────
    left_col, right_col = st.columns([1, 2])

    # ════════════════════════════════════════════════════════════════════════
    # LEFT — photo preview + nav + grouped filmstrip
    # ════════════════════════════════════════════════════════════════════════
    with left_col:
        raw = st.session_state.ps_photo_bytes.get(active_photo.photo_id)
        if not raw and active_photo.filepath:
            fp = Path(active_photo.filepath)
            if fp.exists():
                raw = fp.read_bytes()
                st.session_state.ps_photo_bytes[active_photo.photo_id] = raw

        if raw:
            try:
                img = Image.open(io.BytesIO(raw))
                img = ImageOps.exif_transpose(img)
                # Downscale to compact preview (max 420×210 px)
                prev = img.copy()
                prev.thumbnail((420, 210), Image.LANCZOS)
                if prev.mode in ("RGBA", "P", "LA"):
                    prev = prev.convert("RGB")
                buf = io.BytesIO()
                prev.save(buf, format="JPEG", quality=82)
                st.image(buf.getvalue(), use_container_width=True)
            except Exception:
                st.markdown(
                    '<div style="background:#152e3e;height:100px;display:flex;'
                    'align-items:center;justify-content:center;color:#5c6c75;'
                    'border-radius:4px;font-size:0.82em">Preview unavailable</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="background:#152e3e;height:100px;display:flex;'
                'align-items:center;justify-content:center;color:#5c6c75;'
                'border-radius:4px;font-size:0.82em">File not found</div>',
                unsafe_allow_html=True,
            )

        # ── Filename + Prev / Next ────────────────────────────────────────
        st.markdown(
            f'<div style="font-size:0.70em;color:#5c6c75;margin:2px 0 2px">'
            f'<b style="color:#b8c4c2">#{active_photo.order}</b> · {active_photo.filename}</div>',
            unsafe_allow_html=True,
        )
        pn1, pn2, pn3 = st.columns([1, 2, 1])
        with pn1:
            if active_idx > 0 and st.button("← Prev", key="ps_prev_photo",
                                              use_container_width=True):
                st.session_state.ps_selected_pid = photos[active_idx - 1].photo_id
                st.rerun()
        with pn2:
            st.markdown(
                f'<div style="text-align:center;padding-top:4px;font-size:0.76em;'
                f'color:#5c6c75">{active_idx + 1} / {n}</div>',
                unsafe_allow_html=True,
            )
        with pn3:
            if active_idx < n - 1 and st.button("Next →", key="ps_next_photo",
                                                  use_container_width=True):
                st.session_state.ps_selected_pid = photos[active_idx + 1].photo_id
                st.rerun()

        # ── Grouped thumbnail filmstrip ───────────────────────────────────
        # The component key includes a generation counter so stale events are
        # discarded after each interaction (prevents Prev/Next nav breakage).
        st.markdown('<div style="margin-top:4px"></div>', unsafe_allow_html=True)
        groups = _get_system_groups()
        strip_key = f"ps_sortable_strip_{st.session_state.ps_strip_generation}"
        strip_result = sortable_photo_strip(
            groups=groups,
            thumb_bytes_map=st.session_state.ps_thumb_bytes,
            selected_pid=st.session_state.ps_selected_pid,
            key=strip_key,
        )

        if strip_result is not None:
            # Consume and discard: bump generation so next render starts fresh
            st.session_state.ps_strip_generation += 1
            if strip_result.get("type") == "select":
                st.session_state.ps_selected_pid = strip_result["pid"]
                st.rerun()

        # Re-fetch active_photo in case filmstrip selection changed it
        active_photo, active_idx = _get_selected_photo()
        pid = active_photo.photo_id

        # ── Date settings ─────────────────────────────────────────────────
        with st.expander("⚙️ Date Settings", expanded=False):
            new_inc = st.checkbox(
                "Show date line under each photo",
                value=st.session_state.ps_include_date,
                key="ps_include_date_ck",
            )
            st.session_state.ps_include_date = new_inc
            if new_inc:
                new_gdate = st.text_input(
                    "Global photo date",
                    value=st.session_state.ps_photo_date,
                    key="ps_global_date_inp",
                    placeholder="MM/DD/YYYY",
                )
                st.session_state.ps_photo_date = new_gdate
                per_date = st.text_input(
                    "Override date for this photo",
                    value=active_photo.photo_date,
                    key=f"ps_pdate_{pid}",
                    placeholder="Leave blank to use global date",
                )
                if per_date != active_photo.photo_date:
                    active_photo.photo_date = per_date
                    ps_save_draft()

    # ════════════════════════════════════════════════════════════════════════
    # RIGHT — Photo Inspector (system · view · notes · caption)
    # ════════════════════════════════════════════════════════════════════════
    with right_col:
        # Dark teal card wrapper (open)
        st.markdown(
            '<div style="background:#152e3e;border:1px solid #3d4f58;'
            'border-radius:10px;padding:10px 12px 12px;">',
            unsafe_allow_html=True,
        )

        # ── System context ────────────────────────────────────────────────
        _render_system_context(active_photo)

        # ── Batch apply toggle ────────────────────────────────────────────
        st.checkbox(
            "Apply view type to all photos in this system group",
            value=st.session_state.get("ps_batch_apply", False),
            key="ps_batch_apply",
        )

        # ── Smart view type builder ───────────────────────────────────────
        _render_smart_view_input(active_photo)

        # ── Annotation ───────────────────────────────────────────────────
        st.text_input(
            "Annotation",
            value=active_photo.caption_note,
            key=f"ps_cv_note_{pid}",
            on_change=_on_note_change,
            placeholder='optional — e.g. >4" sediment, cracked frame',
            label_visibility="visible",
        )

        # ── Caption preview ───────────────────────────────────────────────
        live_cap = _rebuild_caption(active_photo)
        no_cap   = "<em style='color:#bbb'>select view type to build caption</em>"
        # Compute group size for context indicator
        sid = active_photo.system_id or "_uncat"
        group_size = sum(
            1 for p in st.session_state.ps_photos
            if (p.system_id or "_uncat") == sid
        )
        group_ctx = (
            f'<span style="color:#8094D4;font-size:0.82em;margin-left:6px">'
            f'#{active_photo.group_order} of {group_size} in group</span>'
            if group_size > 1 else ""
        )
        st.markdown(
            f'<div style="background:#1c2d38;border-left:3px solid #27AD3D;'
            f'border-radius:0 5px 5px 0;padding:6px 10px;margin:6px 0 8px;'
            f'font-size:0.82em;color:#e8edeb;line-height:1.45">'
            f'<span style="color:#5c6c75;font-size:0.78em;text-transform:uppercase;'
            f'letter-spacing:0.06em">Caption</span>{group_ctx}<br>'
            f'<b style="color:#ffffff">({active_photo.order})</b>&nbsp;'
            f'{live_cap if live_cap else no_cap}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Field notes ───────────────────────────────────────────────────
        _render_field_notes(active_photo)

        # ── Remove photo ──────────────────────────────────────────────────
        st.markdown('<div style="margin-top:4px"></div>', unsafe_allow_html=True)
        if st.button("🗑 Remove Photo", key=f"ps_rm_{pid}", use_container_width=True):
            photos.pop(active_idx)
            _renumber(photos)
            if photos:
                new_idx = min(active_idx, len(photos) - 1)
                st.session_state.ps_selected_pid = photos[new_idx].photo_id
            else:
                st.session_state.ps_selected_pid = ""
            st.session_state.ps_ctx_last_pid = ""
            ps_save_draft()
            st.rerun()

        # Gray card wrapper (close)
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _render_export():
    ps_sync_widget_states()
    photos = st.session_state.ps_photos

    st.markdown(
        '<h3 style="color:#ffffff;margin:0 0 8px 0;font-size:1.1em">📤 Export Photosheet</h3>',
        unsafe_allow_html=True,
    )

    if not photos:
        st.warning("No photos to export.", icon="⚠️")
        if st.button("← Back to Upload"):
            st.session_state.ps_step = "upload"
            st.rerun()
        return

    if st.button("← Back to Organize", key="exp_back"):
        st.session_state.ps_step = "organize"
        st.rerun()

    st.markdown("---")
    n = len(photos)

    # Layout — read from sidebar selection (sidebar sets ps_layout via ps_sb_layout_radio)
    layout_keys = list(PS_LAYOUTS.keys())
    sel_layout = st.session_state.get("ps_layout", "3x2")
    if sel_layout not in layout_keys:
        sel_layout = "3x2"
        st.session_state.ps_layout = sel_layout

    cfg = PS_LAYOUTS[sel_layout]
    per_page = cfg["per_page"]
    total_pages = (n + per_page - 1) // per_page
    remainder = n % per_page

    if remainder:
        st.warning(
            f"Last page will have **{per_page - remainder} blank slot(s)** "
            f"({remainder} of {per_page} filled).",
            icon="⚠️",
        )
    st.info(
        f"**{n} photos** → **{total_pages} page(s)** "
        f"({cfg['cols']} col × {cfg['rows']} row = {per_page}/page)",
        icon="📐",
    )

    with st.expander(f"✅ Confirm Order ({n} photos)", expanded=False):
        conf_cols = st.columns(4)
        for i, p in enumerate(photos):
            with conf_cols[i % 4]:
                tb = st.session_state.ps_thumb_bytes.get(p.photo_id, b"")
                if tb:
                    st.image(tb, use_container_width=True)
                st.caption(f"**#{p.order}** {(p.caption or '—')[:26]}")

    with st.expander("📝 Notes Page Preview", expanded=False):
        noted = [p for p in photos if p.notes.strip()]
        if noted:
            for p in noted:
                st.markdown(f"**Photo {p.order}:** {p.notes.strip()}")
        else:
            st.caption("*No field notes — notes page will be omitted.*")

    # Validation
    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:8px 0 4px">Pre-Export Check</div>',
        unsafe_allow_html=True,
    )
    missing_caps = [p for p in photos if not p.caption.strip()]
    missing_files = [p for p in photos if not Path(p.filepath).exists()]
    if missing_caps:
        st.warning(f"{len(missing_caps)} photo(s) have no caption.", icon="⚠️")
    else:
        st.markdown("✅ All photos have captions.")
    if missing_files:
        st.warning(f"{len(missing_files)} photo file(s) not found on disk.", icon="⚠️")
    else:
        st.markdown("✅ All photo files present on disk.")
    if not st.session_state.ps_site_name.strip():
        st.warning("Site name is blank — header will show 'Unknown Site'.", icon="⚠️")

    # Output filename
    st.markdown(
        '<div style="font-size:0.72em;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#b8c4c2;margin:8px 0 4px">Output File</div>',
        unsafe_allow_html=True,
    )
    site_slug = (st.session_state.ps_site_name.strip()
                 .replace(" ", "_").replace("/", "-") or "Site")
    date_slug = (st.session_state.ps_report_date.strip()
                 .replace(" ", "_").replace(",", "") or "Date")
    out_filename = st.text_input(
        "Filename (.docx)",
        value=f"{site_slug}_Photosheet_{date_slug}.docx",
        key="ps_output_filename",
    )
    if not out_filename.endswith(".docx"):
        out_filename += ".docx"

    st.markdown("")
    if st.button("📄 Generate & Download Photosheet",
                 type="primary", use_container_width=True, key="ps_export_btn"):
        ps_sync_widget_states()
        export_photos = [p for p in photos if Path(p.filepath).exists()]
        skipped = len(photos) - len(export_photos)

        if not export_photos:
            st.error("No photos found on disk. Re-upload and try again.", icon="❌")
            return
        if skipped:
            st.warning(f"{skipped} photo(s) skipped (file not found).", icon="⚠️")

        with st.spinner("Building photosheet…"):
            try:
                from app.services.photosheet_builder import build_photosheet
                Path("output").mkdir(exist_ok=True)
                out_path = str(Path("output") / out_filename)
                saved_path = build_photosheet(
                    photos=export_photos,
                    output_path=out_path,
                    layout=sel_layout,
                    site_name=st.session_state.ps_site_name or "Unknown Site",
                    report_date=st.session_state.ps_report_date or "",
                    prepared_by=st.session_state.ps_prepared_by or "",
                    include_date=st.session_state.ps_include_date,
                    global_photo_date=st.session_state.ps_photo_date,
                )
                saved_name = Path(saved_path).name
                docx_bytes = Path(saved_path).read_bytes()

                # Warn if the intended filename was locked by another app
                if saved_name != out_filename:
                    st.warning(
                        f"**{out_filename}** was open in another app — "
                        f"saved as **{saved_name}** instead. "
                        "Close the file in Word and re-export to use the original name.",
                        icon="⚠️",
                    )
                else:
                    st.success(f"Saved: `{saved_path}`", icon="✅")

                st.balloons()
                st.download_button(
                    label="⬇ Download Photosheet",
                    data=docx_bytes,
                    file_name=saved_name,
                    mime=("application/vnd.openxmlformats-officedocument"
                          ".wordprocessingml.document"),
                )
            except Exception as exc:
                st.error(f"Export failed: {exc}", icon="❌")
                st.exception(exc)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render():
    # Sidebar renders first so its widgets exist before main content
    _render_photosheet_sidebar()

    step = st.session_state.get("ps_step", "upload")
    _render_step_indicator(step)

    if step == "upload":
        _render_upload()
    elif step == "organize":
        _render_organize()
    elif step == "export":
        _render_export()
    else:
        st.session_state.ps_step = "upload"
        st.rerun()

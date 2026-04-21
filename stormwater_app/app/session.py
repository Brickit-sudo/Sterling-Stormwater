"""
app/session.py
Central session state management.
All app state lives in st.session_state under the 'project' key (Full Report)
or under 'ps_*' keys (Photosheet mode).
"""

import streamlit as st
from dataclasses import dataclass, field, asdict
from typing import Optional
import uuid
import json
from pathlib import Path


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class ReportMeta:
    site_name: str = ""
    site_address: str = ""
    client_name: str = ""
    report_type: str = "Inspection"          # Inspection | Maintenance | Inspection and Maintenance
    inspection_date: str = ""
    report_date: str = ""
    report_number: str = ""
    prepared_by: str = ""
    weather_conditions: str = ""             # Inspection only
    next_service_date: str = ""              # Maintenance only
    contract_number: str = ""
    site_description: str = ""               # Overall/executive summary — appears in SUMMARY section of DOCX
    # ── Report lifecycle ──────────────────────────────────────────────────────
    status: str = "Draft"                    # Draft | Review | Delivered
    delivered_at: str = ""                   # ISO timestamp when marked Delivered
    delivered_by: str = ""                   # Name of person who delivered
    revision: int = 0                        # Incremented each time a Delivered report is revised


@dataclass
class SystemEntry:
    """One instance of a BMP/stormwater system on site."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    system_type: str = ""       # e.g. "Underdrain Soil Filter"
    system_id: str = ""         # e.g. "USF-1"
    display_name: str = ""      # e.g. "Underdrain Soil Filter 1"
    notes: str = ""
    condition: str = "Good"     # Good | Fair | Poor | N/A


@dataclass
class WriteUp:
    """Editable write-up block for one system entry."""
    entry_id: str = ""          # links to SystemEntry.entry_id
    findings: str = ""
    recommendations: str = ""
    maintenance_performed: str = ""
    post_service_condition: str = ""


@dataclass
class Photo:
    """One photo in the Full Report."""
    photo_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    filename: str = ""
    filepath: str = ""          # absolute path on disk (copied to projects/)
    system_entry_id: str = ""   # links to SystemEntry.entry_id
    system_label: str = ""      # e.g. "Underdrain Soil Filter 1"
    component: str = ""         # e.g. "Outlet Structure"
    view_number: int = 1
    include_date: bool = False
    photo_date: str = ""
    caption_override: str = ""  # if set, use this instead of computed
    display_order: int = 0
    notes: str = ""             # field observations — shown on the notes page

    def computed_caption(self) -> str:
        """Build caption matching Sterling format: (N) System - Component - View label"""
        if self.caption_override:
            return self.caption_override
        parts = [self.system_label or "System"]
        if self.component:
            parts.append(self.component)
        if self.view_number and self.view_number > 0:
            parts.append(f"View {self.view_number}")
        base = f"({self.display_order}) {' - '.join(parts)}"
        if self.include_date and self.photo_date:
            base += f" - {self.photo_date}"
        return base


@dataclass
class PhotosheetPhoto:
    """One photo in the Photosheet workflow."""
    photo_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    filename: str = ""
    filepath: str = ""              # absolute path on disk
    system: str = "Uncategorized"   # systemType — e.g. "Typical Catch Basin"
    caption: str = ""               # full combined caption (rebuilt from components)
    caption_id: str = ""            # systemName — e.g. "CB-1"
    caption_view: str = ""          # viewType — e.g. "Inside View"
    caption_note: str = ""          # optional annotation — e.g. ">6\" sediment"
    notes: str = ""                 # field notes — appears on the notes page only
    photo_date: str = ""            # per-photo date override; falls back to global ps_photo_date
    order: int = 0                  # globalOrder: 1-indexed, sequential across all photos
    system_id: str = ""             # stable UUID for the (system, caption_id) group instance
    group_order: int = 0            # order within the system group (1-indexed)


@dataclass
class ProjectSession:
    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meta: ReportMeta = field(default_factory=ReportMeta)
    systems: list = field(default_factory=list)          # list[SystemEntry]
    write_ups: dict = field(default_factory=dict)        # entry_id -> WriteUp
    photos: list = field(default_factory=list)           # list[Photo]
    imported_text: dict = field(default_factory=dict)    # section -> raw text
    template_path: str = ""


# ── Session helpers ───────────────────────────────────────────────────────────

def init_session():
    """Initialize session state on first load."""
    # Full Report state
    if "project" not in st.session_state:
        st.session_state.project = ProjectSession()
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "photo_bytes" not in st.session_state:
        st.session_state.photo_bytes = {}   # photo_id -> bytes (for display only)
    # Remove legacy app_mode — routing is now sidebar-driven via current_page
    st.session_state.pop("app_mode", None)

    # Photosheet state (ps_ prefix to avoid collisions)
    if "ps_step" not in st.session_state:
        st.session_state.ps_step = "upload"
    if "ps_photos" not in st.session_state:
        st.session_state.ps_photos = []          # list[PhotosheetPhoto]
    if "ps_photo_bytes" not in st.session_state:
        st.session_state.ps_photo_bytes = {}     # photo_id -> full-res bytes
    if "ps_thumb_bytes" not in st.session_state:
        st.session_state.ps_thumb_bytes = {}     # photo_id -> 120px thumbnail bytes
    if "ps_selected_idx" not in st.session_state:
        st.session_state.ps_selected_idx = 0
    if "ps_layout" not in st.session_state:
        st.session_state.ps_layout = "3x2"
    if "ps_site_name" not in st.session_state:
        st.session_state.ps_site_name = ""
    if "ps_report_date" not in st.session_state:
        st.session_state.ps_report_date = ""
    if "ps_prepared_by" not in st.session_state:
        st.session_state.ps_prepared_by = ""
    if "ps_project_id" not in st.session_state:
        st.session_state.ps_project_id = str(uuid.uuid4())
    if "ps_systems" not in st.session_state:
        st.session_state.ps_systems = ["Uncategorized"]   # ordered system group list
    if "ps_selected_pid" not in st.session_state:
        st.session_state.ps_selected_pid = ""             # photo_id of selected photo
    if "ps_include_date" not in st.session_state:
        st.session_state.ps_include_date = False          # show "Date of Photo:" line
    if "ps_photo_date" not in st.session_state:
        st.session_state.ps_photo_date = ""               # global date for all photos
    if "ps_strip_generation" not in st.session_state:
        st.session_state.ps_strip_generation = 0          # bumped after each strip event to clear stale value
    if "ps_uploader_key" not in st.session_state:
        st.session_state.ps_uploader_key = 0              # bumped after each upload batch to reset the widget

    # ── Persistent system context (caption builder) ──────────────────────────
    # These hold the "current working system" that auto-applies to every photo
    # uploaded/captioned, eliminating per-photo re-entry of system type/name.
    if "ps_ctx_sys_type" not in st.session_state:
        st.session_state.ps_ctx_sys_type = ""             # e.g. "Typical Catch Basin"
    if "ps_ctx_sys_name" not in st.session_state:
        st.session_state.ps_ctx_sys_name = ""             # e.g. "CB-1"
    if "ps_ctx_sys_id" not in st.session_state:
        st.session_state.ps_ctx_sys_id = ""               # stable group UUID for (type, name)
    if "ps_ctx_panel_key" not in st.session_state:
        st.session_state.ps_ctx_panel_key = 0             # bumped on Clear to reset panel widgets
    if "ps_ctx_last_pid" not in st.session_state:
        st.session_state.ps_ctx_last_pid = ""             # tracks last selected photo for sync


def get_session(key: str, default=None):
    """Get a top-level session state value."""
    return st.session_state.get(key, default)


def get_project() -> ProjectSession:
    return st.session_state.project


def set_page(page: str):
    st.session_state.current_page = page


def get_write_up(entry_id: str) -> WriteUp:
    """Get or create a WriteUp for a system entry."""
    proj = get_project()
    if entry_id not in proj.write_ups:
        proj.write_ups[entry_id] = WriteUp(entry_id=entry_id)
    return proj.write_ups[entry_id]


def save_project_json(output_dir: str = "projects"):
    """Persist current session to JSON for reload, then sync to DB."""
    proj = get_project()
    proj_dir = Path(output_dir) / proj.project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "project_id": proj.project_id,
        "meta": asdict(proj.meta),
        "systems": [asdict(s) for s in proj.systems],
        "write_ups": {k: asdict(v) for k, v in proj.write_ups.items()},
        "photos": [asdict(p) for p in proj.photos],
        "imported_text": proj.imported_text,
        "template_path": proj.template_path,
    }
    path = proj_dir / "session.json"
    path.write_text(json.dumps(data, indent=2))

    # Sync to SQLite (non-blocking — failure never prevents the JSON save)
    try:
        from app.services.db import upsert_report
        upsert_report(proj)
    except Exception:
        pass

    return str(path)


def load_project_json(path: str):
    """Load a saved project from JSON."""
    data = json.loads(Path(path).read_text())
    proj = get_project()
    proj.project_id = data["project_id"]
    proj.meta = ReportMeta(**data["meta"])
    proj.systems = [SystemEntry(**s) for s in data["systems"]]
    proj.write_ups = {k: WriteUp(**v) for k, v in data["write_ups"].items()}
    proj.photos = [Photo(**p) for p in data["photos"]]
    proj.imported_text = data.get("imported_text", {})
    proj.template_path = data.get("template_path", "")


# ── Photosheet session helpers ────────────────────────────────────────────────

def ps_save_draft(output_dir: str = "projects"):
    """
    Autosave photosheet state to JSON so work survives an accidental refresh.
    File: projects/<ps_project_id>/photosheet_draft.json
    """
    try:
        pid = st.session_state.ps_project_id
        proj_dir = Path(output_dir) / pid
        proj_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "ps_project_id":  pid,
            "ps_site_name":   st.session_state.ps_site_name,
            "ps_report_date": st.session_state.ps_report_date,
            "ps_prepared_by": st.session_state.ps_prepared_by,
            "ps_layout":      st.session_state.ps_layout,
            "ps_step":        st.session_state.ps_step,
            "ps_systems":     st.session_state.ps_systems,
            "ps_include_date": st.session_state.ps_include_date,
            "ps_photo_date":  st.session_state.ps_photo_date,
            "ps_photos": [
                {
                    "photo_id":     p.photo_id,
                    "filename":     p.filename,
                    "filepath":     p.filepath,
                    "system":       p.system,
                    "caption":      p.caption,
                    "caption_id":   p.caption_id,
                    "caption_view": p.caption_view,
                    "caption_note": p.caption_note,
                    "notes":        p.notes,
                    "photo_date":   p.photo_date,
                    "order":        p.order,
                    "system_id":    p.system_id,
                    "group_order":  p.group_order,
                }
                for p in st.session_state.ps_photos
            ],
            # Persistent system context
            "ps_ctx_sys_type": st.session_state.ps_ctx_sys_type,
            "ps_ctx_sys_name": st.session_state.ps_ctx_sys_name,
            "ps_ctx_sys_id":   st.session_state.ps_ctx_sys_id,
        }
        path = proj_dir / "photosheet_draft.json"
        path.write_text(json.dumps(data, indent=2))
        return str(path)
    except Exception:
        return None


def ps_load_draft(draft_path: str):
    """Restore photosheet state from a saved draft JSON."""
    try:
        data = json.loads(Path(draft_path).read_text())
        st.session_state.ps_project_id = data.get("ps_project_id", st.session_state.ps_project_id)
        st.session_state.ps_site_name   = data.get("ps_site_name", "")
        st.session_state.ps_report_date = data.get("ps_report_date", "")
        st.session_state.ps_prepared_by = data.get("ps_prepared_by", "")
        st.session_state.ps_layout      = data.get("ps_layout", "3x2")
        st.session_state.ps_step        = data.get("ps_step", "upload")
        photos = []
        for raw in data.get("ps_photos", []):
            p = PhotosheetPhoto(
                photo_id=raw["photo_id"],
                filename=raw["filename"],
                filepath=raw["filepath"],
                caption=raw.get("caption", ""),
                caption_id=raw.get("caption_id", ""),
                caption_view=raw.get("caption_view", ""),
                caption_note=raw.get("caption_note", ""),
                notes=raw.get("notes", ""),
                system=raw.get("system", "Uncategorized"),
                photo_date=raw.get("photo_date", ""),
                order=raw.get("order", 0),
                system_id=raw.get("system_id", ""),
                group_order=raw.get("group_order", 0),
            )
            photos.append(p)
        st.session_state.ps_photos = photos
        st.session_state.ps_selected_pid = ""
        # Restore system context (backward-compatible — defaults to "" for old drafts)
        st.session_state.ps_ctx_sys_type = data.get("ps_ctx_sys_type", "")
        st.session_state.ps_ctx_sys_name = data.get("ps_ctx_sys_name", "")
        st.session_state.ps_ctx_sys_id   = data.get("ps_ctx_sys_id", "")
        st.session_state.ps_ctx_last_pid = ""   # force re-sync on next organize render
        return True
    except Exception:
        return False


def ps_find_latest_draft(output_dir: str = "projects") -> Optional[str]:
    """Return path to the most recent photosheet draft file, or None."""
    try:
        base = Path(output_dir)
        if not base.exists():
            return None
        drafts = list(base.glob("*/photosheet_draft.json"))
        if not drafts:
            return None
        return str(max(drafts, key=lambda p: p.stat().st_mtime))
    except Exception:
        return None


def ps_sync_widget_states():
    """
    Before export, flush any pending widget state back into photo objects and
    rebuild captions from their components.  Called automatically before export.

    Also flushes the persistent system context panel so the most recently typed
    (but not yet on_change-committed) values are captured.
    """
    # ── Flush context panel widget state ────────────────────────────────────
    ctx_key = st.session_state.get("ps_ctx_panel_key", 0)
    type_wkey = f"ps_ctx_sys_type_dd_{ctx_key}"
    name_wkey = f"ps_ctx_sys_name_inp_{ctx_key}"
    cust_wkey = f"ps_ctx_custom_type_{ctx_key}"

    if type_wkey in st.session_state:
        sel = st.session_state[type_wkey]
        if sel and sel not in ("— select type —", "Custom…"):
            st.session_state.ps_ctx_sys_type = sel
        elif sel == "Custom…" and cust_wkey in st.session_state:
            st.session_state.ps_ctx_sys_type = st.session_state[cust_wkey]
    if name_wkey in st.session_state:
        st.session_state.ps_ctx_sys_name = st.session_state[name_wkey]

    # ── Flush per-photo widget state ─────────────────────────────────────────
    for photo in st.session_state.get("ps_photos", []):
        pid = photo.photo_id
        # Per-photo caption component keys
        view_key = f"ps_cv_view_{pid}"
        note_key = f"ps_cv_note_{pid}"
        fld_key  = f"ps_fld_{pid}"

        if view_key in st.session_state:
            photo.caption_view = st.session_state[view_key]
        if note_key in st.session_state:
            photo.caption_note = st.session_state[note_key]
        if fld_key  in st.session_state:
            photo.notes        = st.session_state[fld_key]

        # Rebuild full caption string from components (skip "Uncategorized")
        sys_part = photo.system if photo.system not in ("", "Uncategorized") else ""
        parts = [p for p in [sys_part, photo.caption_id, photo.caption_view, photo.caption_note] if p.strip()]
        if parts:
            photo.caption = " \u2013 ".join(parts)

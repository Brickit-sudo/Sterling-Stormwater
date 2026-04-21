"""
app/components/sortable_strip.py

Streamlit custom component: grouped photo thumbnail strip.

The component renders in a sandboxed iframe and communicates with Python via
Streamlit's postMessage protocol.  It returns a select action dict:

  {"type": "select", "pid": "<photo_id>"}

Usage
-----
from app.components.sortable_strip import sortable_photo_strip

result = sortable_photo_strip(
    groups=_get_system_groups(),
    thumb_bytes_map=st.session_state.ps_thumb_bytes,
    selected_pid=st.session_state.ps_selected_pid,
)
if result and result["type"] == "select":
    st.session_state.ps_selected_pid = result["pid"]
    st.rerun()
"""

import base64
from pathlib import Path

import streamlit.components.v1 as components

# ── Component registration ────────────────────────────────────────────────────

_COMPONENT_PATH = Path(__file__).parent.parent.parent / "frontend" / "sortable_strip"

_strip_component = components.declare_component(
    "sortable_strip",
    path=str(_COMPONENT_PATH),
)


# ── Public wrapper ────────────────────────────────────────────────────────────

def sortable_photo_strip(
    groups: list,
    thumb_bytes_map: dict,
    selected_pid: str,
    key: str = "ps_sortable_strip",
):
    """
    Render the grouped thumbnail strip and return the user's action.

    Parameters
    ----------
    groups          : list of SystemGroup dicts produced by _get_system_groups():
                      [{system_id, system, caption_id, photos: [PhotosheetPhoto]}]
    thumb_bytes_map : dict mapping photo_id -> raw JPEG bytes (thumbnails)
    selected_pid    : photo_id of the currently active photo
    key             : Streamlit widget key (must be unique on page)

    Returns
    -------
    None until the user clicks a photo; then:
      {"type": "select", "pid": str}
    """
    groups_data = []
    for g in groups:
        photos_list = []
        for p in g["photos"]:
            raw = thumb_bytes_map.get(p.photo_id, b"")
            thumb_src = (
                "data:image/jpeg;base64," + base64.b64encode(raw).decode()
            ) if raw else ""
            photos_list.append({
                "photo_id":    p.photo_id,
                "order":       p.order,
                "group_order": p.group_order,
                "caption":     p.caption or "",
                "thumb_src":   thumb_src,
            })
        groups_data.append({
            "system_id":  g["system_id"],
            "system":     g["system"],
            "caption_id": g["caption_id"],
            "photos":     photos_list,
        })

    return _strip_component(
        groups_data=groups_data,
        selected_pid=selected_pid,
        key=key,
        default=None,
    )

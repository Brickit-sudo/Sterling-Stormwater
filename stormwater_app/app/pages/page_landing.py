"""
app/pages/page_landing.py
Sterling Stormwater — Professional dark enterprise dashboard.

Sections:
  1. Hero band — gradient bg + grid texture + green radial glow
  2. Workflow cards — gradient-border cards with hover animation
  3. File Archive — dark table with hover row highlight
"""

import base64
import json
import datetime
from pathlib import Path

import streamlit as st

_LOGO_PATH = Path("assets/sterling_logo.png")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _logo_b64() -> str:
    if _LOGO_PATH.exists():
        return base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    return ""


def _load_recent_projects(limit: int = 8) -> list[dict]:
    """Scan projects/ for session.json files, most-recently-modified first."""
    projects_dir = Path("projects")
    rows = []
    if not projects_dir.exists():
        return rows
    for f in sorted(
        projects_dir.glob("*/session.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            rows.append({
                "path":     str(f),
                "site":     meta.get("site_name")    or "Untitled Site",
                "client":   meta.get("client_name")  or "—",
                "type":     meta.get("report_type")  or "Full Report",
                "date":     meta.get("report_date")  or meta.get("inspection_date") or "—",
                "status":   meta.get("status", "Draft"),
                "modified": mtime.strftime("%b %d, %Y"),
            })
        except Exception:
            continue
    return rows


def _type_pill(rtype: str) -> str:
    if "photo" in rtype.lower():
        bg, color = "rgba(26,183,56,0.15)", "#1AB738"
    else:
        bg, color = "rgba(56,189,248,0.12)", "#38BDF8"
    return (
        f'<span style="background:{bg};color:{color};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:600;'
        f'padding:3px 9px;border-radius:999px;white-space:nowrap;'
        f'border:1px solid {color}33">{rtype}</span>'
    )


def _status_pill(status: str) -> str:
    spec = {
        "Draft":     ("rgba(107,122,138,0.15)", "#6B7A8A"),
        "Review":    ("rgba(245,158,11,0.15)",  "#F59E0B"),
        "Delivered": ("rgba(26,183,56,0.15)",   "#1AB738"),
    }
    bg, color = spec.get(status, ("rgba(107,122,138,0.15)", "#6B7A8A"))
    return (
        f'<span style="background:{bg};color:{color};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;font-weight:600;'
        f'padding:3px 9px;border-radius:999px;white-space:nowrap;'
        f'border:1px solid {color}44">{status}</span>'
    )


def _section_eyebrow(label: str) -> None:
    st.markdown(
        f'<div style="padding:32px 0 14px 0;">'
        f'<div style="display:flex;align-items:center;gap:10px">'
        f'<div style="width:3px;height:16px;background:#1AB738;border-radius:2px;'
        f'box-shadow:0 0 8px rgba(26,183,56,0.60)"></div>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.12em;'
        f'color:#6B7A8A">{label}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Card styles
# ─────────────────────────────────────────────────────────────────────────────

# Gradient-border wrapper (Linear signature)
_CARD_WRAP = (
    "padding:1px;border-radius:13px;"
    "background:linear-gradient(135deg,"
    "rgba(26,183,56,0.30) 0%,rgba(255,255,255,0.06) 30%,"
    "rgba(255,255,255,0.04) 70%,rgba(26,183,56,0.20) 100%);"
    "transition:background 240ms cubic-bezier(0.16,1,0.3,1),"
    "box-shadow 240ms cubic-bezier(0.16,1,0.3,1);"
)
_CARD_INNER = (
    "background:linear-gradient(180deg,#11384C 0%,#0B2A3C 100%);"
    "border-radius:12px;padding:24px;"
    "position:relative;overflow:hidden;min-height:230px;"
    "box-shadow:0 1px 0 rgba(255,255,255,0.04) inset,0 8px 24px rgba(0,0,0,0.30);"
)
# Muted card for "Coming Soon"
_CARD_WRAP_MUTED = (
    "padding:1px;border-radius:13px;"
    "background:rgba(255,255,255,0.05);"
    "opacity:0.60;"
)
_CARD_INNER_MUTED = (
    "background:linear-gradient(180deg,#0E2F40 0%,#0B2A3C 100%);"
    "border-radius:12px;padding:24px;min-height:230px;"
)

_ICON_BOX = (
    "display:inline-flex;align-items:center;justify-content:center;"
    "width:44px;height:44px;border-radius:10px;"
    "background:rgba(26,183,56,0.12);margin-bottom:14px;"
    "border:1px solid rgba(26,183,56,0.25);"
)
_ICON_BOX_MUTED = (
    "display:inline-flex;align-items:center;justify-content:center;"
    "width:44px;height:44px;border-radius:10px;"
    "background:rgba(255,255,255,0.05);margin-bottom:14px;"
    "border:1px solid rgba(255,255,255,0.08);"
)


def _card_html(icon, eyebrow, title, desc, features) -> str:
    feat_html = "".join(
        f'<li style="padding:2px 0;color:#6B7A8A">{f}</li>'
        for f in features
    )
    return (
        f'<div style="{_CARD_INNER}">'
        # Green radial wash bottom-right
        f'<div style="position:absolute;bottom:-40%;right:-20%;width:60%;height:80%;'
        f'background:radial-gradient(circle,rgba(26,183,56,0.07) 0%,transparent 70%);'
        f'pointer-events:none"></div>'
        # Gradient top edge (Linear hover cue — rendered always at low opacity)
        f'<div style="position:absolute;top:0;left:0;right:0;height:1px;'
        f'background:linear-gradient(90deg,transparent 0%,rgba(26,183,56,0.50) 50%,transparent 100%);'
        f'opacity:0.6"></div>'
        f'<div style="{_ICON_BOX}"><span style="font-size:1.3em">{icon}</span></div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.12em;'
        f'color:#6B7A8A;margin-bottom:6px">{eyebrow}</div>'
        f'<h3 style="font-family:\'Inter\',sans-serif;font-size:1.05em;font-weight:700;'
        f'color:#F1F5F9;margin:0 0 8px 0;letter-spacing:-0.01em">{title}</h3>'
        f'<p style="color:#B8C5D1;font-size:0.84em;margin:0 0 12px 0;line-height:1.55;'
        f'font-weight:450">{desc}</p>'
        f'<ul style="margin:0 0 0 14px;padding:0;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;line-height:1.9;list-style:disc">'
        f'{feat_html}</ul>'
        f'</div>'
    )


def _card_muted_html(icon, eyebrow, title, desc, features) -> str:
    feat_html = "".join(
        f'<li style="padding:2px 0;color:#3D4D5C">{f}</li>'
        for f in features
    )
    return (
        f'<div style="{_CARD_INNER_MUTED}">'
        f'<div style="{_ICON_BOX_MUTED}"><span style="font-size:1.3em">{icon}</span></div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.12em;'
        f'color:#3D4D5C;margin-bottom:6px">{eyebrow}</div>'
        f'<h3 style="font-family:\'Inter\',sans-serif;font-size:1.05em;font-weight:700;'
        f'color:#6B7A8A;margin:0 0 8px 0">{title}</h3>'
        f'<p style="color:#3D4D5C;font-size:0.84em;margin:0 0 12px 0;line-height:1.55">{desc}</p>'
        f'<ul style="margin:0 0 0 14px;padding:0;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;line-height:1.9;list-style:disc">'
        f'{feat_html}</ul>'
        f'</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────────────────

def render():
    # ── Hero ─────────────────────────────────────────────────────────────────
    logo_b64 = _logo_b64()
    logo_tag = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="height:38px;display:block;margin-bottom:20px;'
        f'filter:drop-shadow(0 0 20px rgba(26,183,56,0.35))" />'
        if logo_b64 else
        '<div style="font-size:1.2em;font-weight:700;color:#F1F5F9;margin-bottom:16px">Sterling</div>'
    )

    st.markdown(
        f'''<div style="
            background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(26,183,56,0.09), transparent 60%),
                        linear-gradient(180deg,#0B2A3C 0%,#06141C 100%);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            margin: -0.5rem -1.5rem 0 -1.5rem;
            padding: 44px 48px 40px 48px;
            position: relative; overflow: hidden;">
          <!-- Grid texture -->
          <div style="position:absolute;inset:0;
            background-image:
              linear-gradient(rgba(255,255,255,0.025) 1px,transparent 1px),
              linear-gradient(90deg,rgba(255,255,255,0.025) 1px,transparent 1px);
            background-size:32px 32px;
            -webkit-mask-image:radial-gradient(ellipse 60% 80% at 50% 30%,black 30%,transparent 80%);
            mask-image:radial-gradient(ellipse 60% 80% at 50% 30%,black 30%,transparent 80%);
            pointer-events:none"></div>
          <!-- Content -->
          <div style="position:relative;z-index:1">
            {logo_tag}
            <div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;
              text-transform:uppercase;letter-spacing:0.18em;color:#1AB738;
              margin-bottom:10px;font-weight:600">
              Field Service Platform
            </div>
            <h1 style="font-family:\'Inter\',sans-serif;font-size:2.0em;font-weight:800;
              color:#F1F5F9;margin:0 0 10px 0;letter-spacing:-0.025em;line-height:1.15">
              Sterling Stormwater Reports
            </h1>
            <p style="color:#B8C5D1;font-size:0.92em;margin:0;font-weight:450;
              max-width:520px;line-height:1.6">
              Professional inspection &amp; maintenance documentation —
              faster field-to-desk delivery.
            </p>
          </div>
        </div>''',
        unsafe_allow_html=True,
    )

    # ── Workflow cards ────────────────────────────────────────────────────────
    _section_eyebrow("Start a Workflow")

    col_a, col_b, col_c = st.columns(3, gap="medium")

    with col_a:
        st.markdown(
            f'<div style="{_CARD_WRAP}">'
            + _card_html(
                "📷", "Workflow A", "Photosheet",
                "Upload, caption, and arrange site photos. Export a branded photo sheet in one click.",
                ["Bulk upload &amp; auto-sort by system",
                 "3×2 · 3×3 · 2×2 · Full-page layouts",
                 "Caption &amp; field notes editor",
                 "Auto notes page in output"],
            )
            + '</div>',
            unsafe_allow_html=True,
        )
        if st.button("📷  Open Photosheet", key="mode_photosheet",
                     type="primary", use_container_width=True):
            st.session_state.current_page = "photosheet"
            st.session_state.ps_step      = "upload"
            st.rerun()

    with col_b:
        st.markdown(
            f'<div style="{_CARD_WRAP}">'
            + _card_html(
                "📄", "Workflow B", "Full Report",
                "Build a complete Sterling-format inspection or maintenance report with cover page and write-ups.",
                ["Auto-fill from prior report",
                 "System-by-system write-ups",
                 "Branded cover page + certification",
                 "Inspection · Maintenance · Combined"],
            )
            + '</div>',
            unsafe_allow_html=True,
        )
        if st.button("📄  Start Full Report", key="mode_fullreport",
                     use_container_width=True):
            st.session_state.current_page = "setup"
            st.rerun()

    with col_c:
        st.markdown(
            f'<div style="{_CARD_WRAP_MUTED}">'
            + _card_muted_html(
                "🗂️", "Coming Soon", "Templates",
                "Reusable report templates for recurring sites. Pre-fill all systems and write-up scaffolding.",
                ["Site-specific presets",
                 "Auto-system builder",
                 "Write-up template libraries",
                 "One-click report scaffold"],
            )
            + '</div>',
            unsafe_allow_html=True,
        )
        st.button("🔒  Templates — Coming Soon", key="mode_templates",
                  use_container_width=True, disabled=True)

    # ── File Archive ──────────────────────────────────────────────────────────
    _section_eyebrow("File Archive")

    # Search + View All row
    s_col, b_col = st.columns([5, 1])
    with s_col:
        search = st.text_input(
            "search",
            placeholder="🔍  Search by site, client, or report type…",
            label_visibility="collapsed",
            key="landing_archive_search",
        )
    with b_col:
        if st.button("View All →", key="archive_view_all", use_container_width=True):
            st.session_state.current_page = "library"
            st.rerun()

    projects = _load_recent_projects(limit=8)
    if search:
        q = search.lower()
        projects = [p for p in projects
                    if q in p["site"].lower()
                    or q in p["client"].lower()
                    or q in p["type"].lower()]

    # Dark table container
    st.markdown(
        '<div style="background:linear-gradient(180deg,#0E2F40 0%,#0B2A3C 100%);"'
        'border:1px solid rgba(255,255,255,0.06);border-radius:10px;overflow:hidden;'
        'box-shadow:0 1px 0 rgba(255,255,255,0.04) inset,0 8px 24px rgba(0,0,0,0.25);">',
        unsafe_allow_html=True,
    )

    if not projects:
        st.markdown(
            '<div style="text-align:center;padding:48px 0;">'
            '<div style="font-size:2.2em;margin-bottom:10px;opacity:0.4">📂</div>'
            '<div style="font-family:\'Inter\',sans-serif;font-weight:600;'
            'color:#B8C5D1;font-size:0.92em;margin-bottom:4px">No archives yet</div>'
            '<div style="font-size:0.82em;color:#6B7A8A">'
            'Generate your first report to build your archive.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # Table header
        st.markdown(
            '<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 80px;'
            'gap:0;padding:12px 16px;'
            'background:rgba(21,69,94,0.50);'
            'border-bottom:1px solid rgba(255,255,255,0.06);">'
            + "".join(
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:0.10em;color:#6B7A8A;font-weight:600">'
                f'{h}</div>'
                for h in ["Site / Client", "Type", "Date", "Status", ""]
            )
            + '</div>',
            unsafe_allow_html=True,
        )

        for i, proj in enumerate(projects):
            is_last = i == len(projects) - 1
            border_b = "" if is_last else "border-bottom:1px solid rgba(255,255,255,0.04);"
            row_cols = st.columns([2, 1, 1, 1, 0.6])
            with row_cols[0]:
                st.markdown(
                    f'<div style="padding:13px 0 13px 16px;{border_b}">'
                    f'<div style="font-size:0.88em;font-weight:600;color:#F1F5F9;'
                    f'font-family:\'Inter\',sans-serif">{proj["site"]}</div>'
                    f'<div style="font-size:0.76em;color:#6B7A8A;margin-top:2px">'
                    f'{proj["client"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[1]:
                st.markdown(
                    f'<div style="padding:14px 0;{border_b}">'
                    f'{_type_pill(proj["type"])}</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[2]:
                st.markdown(
                    f'<div style="padding:14px 0;font-size:0.83em;color:#B8C5D1;{border_b}">'
                    f'{proj["modified"]}</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[3]:
                st.markdown(
                    f'<div style="padding:14px 0;{border_b}">'
                    f'{_status_pill(proj["status"])}</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[4]:
                if st.button("Open", key=f"arch_open_{i}", use_container_width=True):
                    try:
                        from app.session import load_project_json, set_page
                        load_project_json(proj["path"])
                        set_page("setup")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not load: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center;padding:36px 0 8px 0;">'
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
        'color:#3D4D5C;letter-spacing:0.08em">'
        'Sterling Stormwater Maintenance Services, Inc'
        ' &nbsp;·&nbsp; Report Generator v1.0'
        '</div></div>',
        unsafe_allow_html=True,
    )

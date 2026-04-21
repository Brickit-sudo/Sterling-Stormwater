"""
app/pages/page_library.py
Report Library — browse all clients, sites, and their report history.

Provides:
  - Searchable site/client tree
  - Per-site report list with condition badges and system tags
  - One-click load of any past session into the current workspace
"""

import json
from pathlib import Path
import streamlit as st

from app.components.ui_helpers import section_header
from app.services.db import (
    get_all_sites,
    get_reports_for_site,
    get_condition_history,
)
from app.session import load_project_json, get_project, set_page

_COND_COLOR = {
    "Good":  ("rgba(26,183,56,0.15)",   "#1AB738"),
    "Fair":  ("rgba(245,158,11,0.15)",  "#F59E0B"),
    "Poor":  ("rgba(244,63,94,0.15)",   "#F43F5E"),
    "N/A":   ("rgba(107,122,138,0.12)", "#6B7A8A"),
}


def _condition_badge(condition: str) -> str:
    bg, color = _COND_COLOR.get(condition, ("rgba(107,122,138,0.12)", "#6B7A8A"))
    return (
        f'<span style="background:{bg};color:{color};font-weight:600;'
        f'padding:3px 9px;border-radius:999px;font-size:11px;'
        f'font-family:\'JetBrains Mono\',monospace;'
        f'border:1px solid {color}33">{condition}</span>'
    )


def _status_badge(status: str) -> str:
    spec = {
        "Draft":     ("rgba(107,122,138,0.12)", "#6B7A8A"),
        "Review":    ("rgba(245,158,11,0.12)",  "#F59E0B"),
        "Delivered": ("rgba(26,183,56,0.12)",   "#1AB738"),
    }
    bg, color = spec.get(status, ("rgba(107,122,138,0.12)", "#6B7A8A"))
    return (
        f'<span style="background:{bg};color:{color};'
        f'padding:3px 8px;border-radius:999px;font-size:11px;'
        f'font-family:\'JetBrains Mono\',monospace;font-weight:600;'
        f'border:1px solid {color}44">{status}</span>'
    )


def render():
    section_header(
        "Report Library",
        "Browse all sites and their full inspection history."
    )

    # ── Search bar ────────────────────────────────────────────────────────────
    search = st.text_input(
        "🔍 Search by site or client name",
        key="lib_search",
        placeholder="e.g. Riverside Commons, ABC Corp…",
        label_visibility="collapsed",
    )

    sites = get_all_sites(search)

    if not sites:
        if search:
            st.info(f"No sites matching **{search}**.")
        else:
            st.info(
                "No reports saved yet. Complete a Full Report and click **Save** "
                "in the sidebar to begin building your library.",
                icon="📚",
            )
        return

    st.caption(f"{len(sites)} site(s) found")
    st.markdown("---")

    # ── Group sites by client ──────────────────────────────────────────────────
    by_client: dict[str, list[dict]] = {}
    for s in sites:
        by_client.setdefault(s["client_name"], []).append(s)

    proj = get_project()

    for client_name, client_sites in by_client.items():
        st.markdown(
            f'<div style="font-size:0.78em;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.10em;color:#6B7A8A;margin:14px 0 4px 0">'
            f'{client_name}</div>',
            unsafe_allow_html=True,
        )

        for site in client_sites:
            site_id      = site["site_id"]
            site_name    = site["site_name"]
            address      = site.get("address") or ""
            report_count = site.get("report_count", 0)

            addr_tag = f" · {address}" if address else ""
            expander_label = (
                f"{site_name}{addr_tag}  —  {report_count} report(s)"
            )

            with st.expander(expander_label, expanded=False):
                reports = get_reports_for_site(site_id)

                if not reports:
                    st.caption("No reports on file.")
                    continue

                for row in reports:
                    is_current   = row["report_id"] == proj.project_id
                    date_str     = row.get("inspection_date") or row.get("report_date") or "—"
                    rtype        = row.get("report_type", "—")
                    rnum         = row.get("report_number") or ""
                    prep         = row.get("prepared_by") or "—"
                    cond         = row.get("condition_summary") or "N/A"
                    status       = row.get("status", "Draft")
                    json_path    = row.get("session_json_path", "")

                    try:
                        systems = json.loads(row.get("systems_summary_json") or "[]")
                    except Exception:
                        systems = []

                    system_tags_html = " ".join(
                        f'<span style="background:rgba(56,189,248,0.08);padding:2px 8px;'
                        f'border-radius:999px;font-size:11px;'
                        f'border:1px solid rgba(56,189,248,0.20);color:#38BDF8;'
                        f'font-family:\'JetBrains Mono\',monospace;font-weight:500">'
                        f'{s.get("system_id","")}</span>'
                        for s in systems if s.get("system_id")
                    )

                    current_marker = (
                        ' <em style="color:#1AB738;font-size:12px">(current)</em>'
                        if is_current else ""
                    )
                    num_part = f"  ·  #{rnum}" if rnum else ""

                    st.markdown(
                        f'<div style="padding:11px 14px;margin-bottom:5px;border-radius:8px;'
                        f'background:linear-gradient(180deg,#103447,#0E2F40);'
                        f'border:1px solid rgba(255,255,255,0.06);'
                        f'border-left:3px solid {"#1AB738" if is_current else "rgba(255,255,255,0.06)"};">'
                        f'<div style="font-weight:600;font-size:13px;color:#F1F5F9;'
                        f'font-family:\'Inter\',sans-serif;margin-bottom:4px">'
                        f'{date_str} · {rtype}{num_part}{current_marker}</div>'
                        f'<div style="font-size:12px;color:#B8C5D1;margin:4px 0;'
                        f'display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
                        f'<span style="color:#6B7A8A">Prepared by: {prep}</span>'
                        f'&nbsp;·&nbsp; Overall: {_condition_badge(cond)}'
                        f'&nbsp;·&nbsp; {_status_badge(status)}'
                        f'</div>'
                        f'<div style="margin-top:6px;display:flex;gap:5px;flex-wrap:wrap">'
                        f'{system_tags_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Load button — only if the session JSON exists on disk
                    if json_path and Path(json_path).exists() and not is_current:
                        load_key = f"lib_load_{row['report_id']}"
                        if st.button(
                            f"📂 Load this report",
                            key=load_key,
                            help=f"Load {date_str} · {rtype} into the current workspace",
                        ):
                            try:
                                load_project_json(json_path)
                                set_page("setup")
                                st.success(
                                    f"Loaded: {site_name} — {date_str}", icon="✅"
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Could not load session: {exc}")
                    elif is_current:
                        st.caption("*This report is already open.*")

                # ── Mini condition trend for this site ───────────────────────
                history = get_condition_history(site_id)
                if len(history) >= 2:
                    with st.expander("📈 Condition trend", expanded=False):
                        try:
                            import plotly.graph_objects as go

                            _MAP = {"Poor": 1, "Fair": 2, "Good": 3}
                            by_sys: dict[str, list] = {}
                            for h in history:
                                label = h.get("display_name") or h.get("system_id") or "?"
                                by_sys.setdefault(label, []).append(h)

                            fig = go.Figure()
                            for label, entries in by_sys.items():
                                pts = sorted(
                                    [e for e in entries if _MAP.get(e["condition"])],
                                    key=lambda e: e.get("date", ""),
                                )
                                if not pts:
                                    continue
                                fig.add_trace(go.Scatter(
                                    x=[e["date"] for e in pts],
                                    y=[_MAP[e["condition"]] for e in pts],
                                    text=[e["condition"] for e in pts],
                                    mode="lines+markers",
                                    name=label,
                                    hovertemplate="%{x}<br>" + label + ": <b>%{text}</b><extra></extra>",
                                    marker={"size": 8},
                                ))
                            fig.update_layout(
                                yaxis=dict(tickvals=[1, 2, 3], ticktext=["Poor", "Fair", "Good"],
                                           range=[0.5, 3.5],
                                           gridcolor="rgba(255,255,255,0.06)",
                                           tickfont=dict(color="#6B7A8A")),
                                xaxis=dict(gridcolor="rgba(255,255,255,0.06)",
                                           tickfont=dict(color="#6B7A8A")),
                                height=260,
                                margin={"t": 20, "b": 30, "l": 50, "r": 10},
                                plot_bgcolor="#0E2F40", paper_bgcolor="#103447",
                                showlegend=len(by_sys) > 1,
                                legend=dict(orientation="h", y=1.05,
                                            font=dict(color="#B8C5D1")),
                                font=dict(family="Inter, Segoe UI, sans-serif",
                                          color="#B8C5D1"),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        except ImportError:
                            st.caption("Install plotly to view trend charts.")

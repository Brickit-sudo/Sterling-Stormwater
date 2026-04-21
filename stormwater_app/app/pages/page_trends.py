"""
app/pages/page_trends.py
Site History — condition trend charts and report history for the current site.

Requires at least 2 saved reports for the same Client + Site to show trends.
"""

import json
from pathlib import Path
import streamlit as st

from app.session import get_project
from app.services.db import get_site_for_project, get_condition_history, get_reports_for_site
from app.components.ui_helpers import section_header


_COND_MAP   = {"Poor": 1, "Fair": 2, "Good": 3}
_COND_LABEL = {1: "Poor", 2: "Fair", 3: "Good"}
_COND_COLOR = {"Good": "#27AD3D", "Fair": "#d48b00", "Poor": "#cc2222", "N/A": "#888888"}


def _condition_badge(condition: str) -> str:
    color = _COND_COLOR.get(condition, "#888")
    return (
        f'<span style="background:{color};color:white;font-weight:bold;'
        f'padding:2px 10px;border-radius:10px;font-size:0.82em">{condition}</span>'
    )


def render():
    section_header(
        "Site History",
        "Condition trends and report history for the current site."
    )

    proj        = get_project()
    meta        = proj.meta
    client_name = meta.client_name or ""
    site_name   = meta.site_name   or ""

    if not client_name or not site_name:
        st.info(
            "Complete the **Client** and **Site Name** fields on the Setup page "
            "to view site history.",
            icon="ℹ️",
        )
        return

    site = get_site_for_project(client_name, site_name)
    if not site:
        st.info(
            f"No saved history found for **{client_name} — {site_name}**. "
            "Save this project to start building a history.",
            icon="ℹ️",
        )
        return

    site_id = site["site_id"]
    reports  = get_reports_for_site(site_id)

    st.markdown(
        f"### {site_name}"
        f'<span style="color:#888;font-size:0.85em;font-weight:normal"> — {client_name}</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"{len(reports)} report(s) on file · {site.get('address') or 'No address recorded'}")

    if not reports:
        st.info("No reports saved yet for this site.")
        return

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab_trends, tab_history, tab_photos = st.tabs(
        ["📈 Condition Trends", "📋 Report History", "🖼 Photo Comparison"]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 1: Condition Trend Charts
    # ══════════════════════════════════════════════════════════════════════════
    with tab_trends:
        history = get_condition_history(site_id)
        if not history:
            st.info("No condition data available yet.")
        else:
            # Group by display_name (fall back to system_id)
            by_system: dict[str, list[dict]] = {}
            for h in history:
                label = h.get("display_name") or h.get("system_id") or "Unknown"
                by_system.setdefault(label, []).append(h)

            # Filter out systems with only N/A ratings
            plottable = {
                k: v for k, v in by_system.items()
                if any(_COND_MAP.get(e["condition"]) for e in v)
            }

            if not plottable:
                st.info("All recorded conditions are N/A — no trend data to chart.")
            else:
                try:
                    import plotly.graph_objects as go

                    fig = go.Figure()
                    for label, entries in plottable.items():
                        entries_sorted = sorted(entries, key=lambda e: e.get("date", ""))
                        dates  = [e["date"] for e in entries_sorted if _COND_MAP.get(e["condition"])]
                        nums   = [_COND_MAP[e["condition"]] for e in entries_sorted if _COND_MAP.get(e["condition"])]
                        labels = [e["condition"] for e in entries_sorted if _COND_MAP.get(e["condition"])]

                        if not dates:
                            continue

                        fig.add_trace(go.Scatter(
                            x=dates,
                            y=nums,
                            mode="lines+markers",
                            name=label,
                            text=labels,
                            hovertemplate="%{x}<br>" + label + ": <b>%{text}</b><extra></extra>",
                            marker={"size": 10},
                            line={"width": 2},
                        ))

                    fig.update_layout(
                        yaxis=dict(
                            tickvals=[1, 2, 3],
                            ticktext=["Poor", "Fair", "Good"],
                            range=[0.5, 3.5],
                            title="Condition",
                            gridcolor="#e0e0e0",
                        ),
                        xaxis=dict(title="Inspection Date"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                        height=380,
                        margin={"t": 40, "b": 40, "l": 60, "r": 20},
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                    )
                    # Add horizontal band for condition zones
                    fig.add_hrect(y0=0.5, y1=1.5, fillcolor="#ffcccc", opacity=0.15, line_width=0)
                    fig.add_hrect(y0=1.5, y1=2.5, fillcolor="#fff3cc", opacity=0.15, line_width=0)
                    fig.add_hrect(y0=2.5, y1=3.5, fillcolor="#ccffcc", opacity=0.15, line_width=0)

                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "Green zone = Good · Yellow zone = Fair · Red zone = Poor · "
                        "N/A ratings are excluded from the chart."
                    )

                except ImportError:
                    st.warning("Install plotly (`pip install plotly`) to view trend charts.")
                    # Fallback: simple table
                    rows = []
                    for label, entries in plottable.items():
                        for e in sorted(entries, key=lambda x: x.get("date", "")):
                            rows.append({"System": label, "Date": e["date"], "Condition": e["condition"]})
                    st.dataframe(rows, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 2: Report History Table
    # ══════════════════════════════════════════════════════════════════════════
    with tab_history:
        for row in reports:
            is_current = row["report_id"] == proj.project_id
            status     = row.get("status", "Draft")
            label_color = _COND_COLOR.get(row.get("condition_summary", ""), "#888")
            border_style = "border-left: 4px solid #27AD3D;" if is_current else "border-left: 4px solid #ddd;"

            date_str = row.get("inspection_date") or row.get("report_date") or "—"
            rtype    = row.get("report_type", "—")
            rnum     = row.get("report_number") or ""
            prep     = row.get("prepared_by")   or "—"
            cond     = row.get("condition_summary") or "N/A"

            badge_html  = _condition_badge(cond)
            current_tag = " <em style='color:#27AD3D'>(current)</em>" if is_current else ""

            try:
                systems = json.loads(row.get("systems_summary_json") or "[]")
            except Exception:
                systems = []

            system_tags = "  ".join(
                f'<span style="background:#f0f0f0;padding:1px 7px;border-radius:8px;'
                f'font-size:0.78em">{s.get("system_id","")}</span>'
                for s in systems if s.get("system_id")
            )

            st.markdown(
                f'<div style="padding:10px 14px;margin-bottom:8px;border-radius:6px;'
                f'background:#fafafa;{border_style}">'
                f'<div style="font-weight:bold;font-size:0.95em">'
                f'{date_str} · {rtype}{f"  ·  #{rnum}" if rnum else ""}{current_tag}</div>'
                f'<div style="font-size:0.85em;color:#555;margin:2px 0">'
                f'Prepared by: {prep} &nbsp;·&nbsp; Overall: {badge_html} &nbsp;·&nbsp; Status: {status}</div>'
                f'<div style="margin-top:4px">{system_tags}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # Tab 3: Photo Comparison
    # ══════════════════════════════════════════════════════════════════════════
    with tab_photos:
        st.caption(
            "Compare photos of the same system component across inspection visits. "
            "Select a system and component below."
        )

        # Collect all photos across all reports at this site
        all_photos_by_system: dict[str, list[dict]] = {}
        for row in reports:
            json_path = row.get("session_json_path", "")
            if not json_path:
                continue
            try:
                data    = json.loads(Path(json_path).read_text(encoding="utf-8"))
                systems = {s["entry_id"]: s.get("display_name", s.get("system_id", ""))
                           for s in data.get("systems", [])}
                date    = (data.get("meta", {}).get("inspection_date") or
                           data.get("meta", {}).get("report_date") or "")
                for p in data.get("photos", []):
                    sys_label = systems.get(p.get("system_entry_id", ""), "Unknown")
                    component  = p.get("component", "")
                    group_key  = f"{sys_label} — {component}" if component else sys_label
                    all_photos_by_system.setdefault(group_key, []).append({
                        "filepath":  p.get("filepath", ""),
                        "caption":   p.get("caption_override") or
                                     f"({p.get('display_order','')}) {sys_label}"
                                     f"{' — ' + component if component else ''}",
                        "date":      date,
                        "report_id": row["report_id"],
                    })
            except Exception:
                continue

        if not all_photos_by_system:
            st.info("No photos found across reports for this site.")
        else:
            groups    = sorted(all_photos_by_system.keys())
            sel_group = st.selectbox("System / Component", groups, key="compare_group")
            photos    = sorted(
                all_photos_by_system[sel_group],
                key=lambda p: p.get("date", ""),
            )

            if not photos:
                st.info("No photos for this selection.")
            else:
                cols = st.columns(min(len(photos), 3))
                for i, photo in enumerate(photos):
                    fp = Path(photo["filepath"])
                    with cols[i % len(cols)]:
                        if fp.exists():
                            try:
                                from app.services.photo_service import correct_orientation_bytes
                                img_bytes = correct_orientation_bytes(fp.read_bytes())
                                st.image(img_bytes, use_container_width=True)
                            except Exception:
                                st.image(str(fp), use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="background:#f0f0f0;height:140px;display:flex;'
                                'align-items:center;justify-content:center;color:#aaa;'
                                'font-size:0.8em;border:1px dashed #ccc">Photo not found</div>',
                                unsafe_allow_html=True,
                            )
                        st.caption(f"**{photo.get('date','—')}**  \n{photo['caption']}")

"""
app/pages/page_sites.py
Site Database — Excel-like editable table of all client sites.
Stores data in data/sites.json relative to the app root.
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from app.components.ui_helpers import section_header

_DATA_PATH = Path("data/sites.json")

_COLUMNS = {
    "site_name":             "Site Name",
    "client_name":           "Client",
    "site_address":          "Address",
    "contract_number":       "Contract #",
    "inspection_frequency":  "Frequency",
    "last_inspection":       "Last Inspection",
    "next_service":          "Next Service",
    "bmp_count":             "BMP Count",
    "status":                "Status",
    "notes":                 "Notes",
}

_FREQ_OPTIONS   = ["Quarterly", "Semi-Annual", "Annual", "As Needed"]
_STATUS_OPTIONS = ["Active", "On Hold", "Completed", "Prospect"]

_EMPTY_ROW = {
    "site_name":            "",
    "client_name":          "",
    "site_address":         "",
    "contract_number":      "",
    "inspection_frequency": "Quarterly",
    "last_inspection":      "",
    "next_service":         "",
    "bmp_count":            0,
    "status":               "Active",
    "notes":                "",
}


def _load() -> list[dict]:
    try:
        if _DATA_PATH.exists():
            return json.loads(_DATA_PATH.read_text())
    except Exception:
        pass
    return []


def _save(rows: list[dict]) -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(rows, indent=2))


def _to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame([_EMPTY_ROW])
    return pd.DataFrame(rows)


def _from_df(df: pd.DataFrame) -> list[dict]:
    df = df.fillna("").copy()
    df["bmp_count"] = pd.to_numeric(df["bmp_count"], errors="coerce").fillna(0).astype(int)
    return df.to_dict(orient="records")


def _summary_cards(rows: list[dict]) -> None:
    active   = sum(1 for r in rows if r.get("status") == "Active")
    prospect = sum(1 for r in rows if r.get("status") == "Prospect")
    overdue  = 0
    try:
        from datetime import date
        today = date.today()
        for r in rows:
            ns = r.get("next_service", "")
            if ns:
                d = date.fromisoformat(ns)
                if d < today and r.get("status") == "Active":
                    overdue += 1
    except Exception:
        pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sites",    len(rows))
    c2.metric("Active",         active)
    c3.metric("Prospects",      prospect)
    c4.metric("Overdue Service", overdue,
              delta=f"-{overdue} past due" if overdue else None,
              delta_color="inverse")


def render():
    section_header("Site Database", "Your complete client site directory — edit inline.")

    rows = _load()

    # ── Summary cards ─────────────────────────────────────────────────────────
    if rows:
        _summary_cards(rows)
        st.markdown("---")

    # ── Toolbar ───────────────────────────────────────────────────────────────
    col_add, col_save, col_exp, col_imp, _ = st.columns([1, 1, 1, 1, 4])

    with col_add:
        add_row = st.button("➕ Add Site", use_container_width=True)
    with col_save:
        save_btn = st.button("💾 Save", use_container_width=True, type="primary")
    with col_exp:
        csv_preview = _to_df(rows).to_csv(index=False)
        st.download_button(
            "⬇ Export CSV", data=csv_preview,
            file_name="sterling_sites.csv", mime="text/csv",
            use_container_width=True, key="sites_dl_top",
        )
    with col_imp:
        show_import = st.button("⬆ Import CSV", use_container_width=True)

    if add_row:
        rows.append(dict(_EMPTY_ROW))
        _save(rows)
        st.rerun()

    if show_import:
        st.session_state["_sites_show_import"] = not st.session_state.get("_sites_show_import", False)

    if st.session_state.get("_sites_show_import"):
        uploaded = st.file_uploader(
            "Upload a CSV with columns matching the table headers",
            type=["csv"], key="sites_csv_import",
        )
        if uploaded:
            try:
                df_imp = pd.read_csv(uploaded)
                for col, default in _EMPTY_ROW.items():
                    if col not in df_imp.columns:
                        df_imp[col] = default
                rows = _from_df(df_imp[list(_EMPTY_ROW.keys())])
                _save(rows)
                st.success(f"Imported {len(rows)} rows.")
                st.session_state["_sites_show_import"] = False
                st.rerun()
            except Exception as exc:
                st.error(f"Import failed: {exc}")

    # ── Editable data table ───────────────────────────────────────────────────
    df = _to_df(rows)

    column_config = {
        "site_name":            st.column_config.TextColumn("Site Name",       width="medium"),
        "client_name":          st.column_config.TextColumn("Client",          width="medium"),
        "site_address":         st.column_config.TextColumn("Address",         width="large"),
        "contract_number":      st.column_config.TextColumn("Contract #",      width="small"),
        "inspection_frequency": st.column_config.SelectboxColumn(
                                    "Frequency", options=_FREQ_OPTIONS, width="small"),
        "last_inspection":      st.column_config.TextColumn("Last Inspection",
                                    help="YYYY-MM-DD",   width="small"),
        "next_service":         st.column_config.TextColumn("Next Service",
                                    help="YYYY-MM-DD",   width="small"),
        "bmp_count":            st.column_config.NumberColumn("BMPs", min_value=0,
                                    max_value=999, step=1, width="small"),
        "status":               st.column_config.SelectboxColumn(
                                    "Status", options=_STATUS_OPTIONS, width="small"),
        "notes":                st.column_config.TextColumn("Notes",           width="large"),
    }

    edited = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="sites_editor",
    )

    if save_btn:
        updated = _from_df(edited)
        _save(updated)
        st.toast("Site database saved!", icon="✅")
        st.rerun()

    # ── Quick-fill from recent projects ──────────────────────────────────────
    st.markdown("---")
    with st.expander("⚡ Import site from a recent project", expanded=False):
        st.caption(
            "Quickly populate a row from any project you have open or recently saved. "
            "Open a project first via the Full Report workflow, then click below."
        )
        try:
            from app.session import get_project
            proj = get_project()
            meta = proj.meta
            if meta.site_name:
                st.markdown(
                    f"**Current project:** {meta.site_name} — {meta.client_name or '(no client)'}"
                )
                if st.button("Add this project's site to database", key="sites_from_proj"):
                    new_row = dict(_EMPTY_ROW)
                    new_row.update({
                        "site_name":       meta.site_name,
                        "client_name":     meta.client_name,
                        "site_address":    meta.site_address,
                        "contract_number": meta.contract_number,
                        "last_inspection": meta.inspection_date,
                        "next_service":    meta.next_service_date,
                    })
                    current_rows = _load()
                    existing = [r["site_name"] for r in current_rows]
                    if meta.site_name not in existing:
                        current_rows.append(new_row)
                        _save(current_rows)
                        st.success(f"Added {meta.site_name}.")
                        st.rerun()
                    else:
                        st.info(f"{meta.site_name} is already in the database.")
            else:
                st.caption("No active project loaded.")
        except Exception:
            st.caption("Load a project first.")

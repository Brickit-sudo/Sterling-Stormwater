# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

All commands run from `stormwater_app/`:

```bash
# Start the app (opens at http://localhost:8501)
streamlit run app.py

# If port 8501 is busy
streamlit run app.py --server.port 8502

# Install dependencies
pip install -r requirements.txt

# Regenerate the Word template (run once after install, or after deleting templates/report_template.docx)
python create_template.py
```

There are no automated tests or linting configurations.

## Architecture Overview

### Two Distinct Workflows

The app has two independent workflows selected from the landing page (`app/pages/page_landing.py`), routed via `st.session_state.app_mode`:

1. **Photosheet mode** (`app_mode = "photosheet"`) — standalone photo-upload and caption tool. Renders `page_photosheet.py` directly, no sidebar. Saves drafts as `projects/{uuid}/photosheet_draft.json`.

2. **Full Report mode** (`app_mode = "fullreport"`) — multi-step report builder with sidebar navigation. 4-page flow: Setup → Systems → Write-Ups → Export. Saves session as `projects/{uuid}/session.json`.

`app.py` is the router — it checks `app_mode` and dispatches accordingly.

### Session State Architecture

All mutable data lives in `st.session_state`. Two namespaces:

- **Full Report**: `st.session_state.project` holds a `ProjectSession` dataclass (defined in `app/session.py`). Page navigation is `st.session_state.current_page`.
- **Photosheet**: `ps_*` prefixed keys (e.g. `ps_photos`, `ps_step`, `ps_site_name`). No single container object.

`init_session()` in `app/session.py` is called on every Streamlit rerun and initializes missing keys. `get_project()` returns the `ProjectSession` object.

### DOCX Generation

There are **two separate DOCX builders**:

- `app/services/report_builder.py` — Full Report builder. Entry point: `build_report(proj, filename, template_path, photo_grid)`. Outputs to `output/`.
- `app/services/photosheet_builder.py` — Photosheet builder. Uses native Word header/footer architecture (no manual page breaks). Body is a single continuous table that Word paginates naturally.

**Critical detail in `report_builder.py`**: The cover page uses a "build flat, then rearrange XML" pattern. Content is appended to the document body, then lxml elements are extracted and injected into a 3-row borderless outer table (Row 0: header/info, Row 1: findings flex zone, Row 2: certification anchored to bottom). This is necessary because `python-docx`'s `Cell.add_table()` has a paragraph-ordering bug. The interior body builder functions (`_build_inspection_body`, `_build_maintenance_body`, `_build_combined_body`) exist in the file but are **not called** — all content goes on the cover page.

### Page-Fit Algorithm

`app/services/page_fit.py` runs before cover page generation. It estimates content height from font metrics (Calibri proportional character width factor: 0.655, line height factor: 1.20) and applies staged compression (strip spacing → zero cell padding → scale font 8.5→7.0pt → scale logo 3.6→2.5") to keep everything on page 1. The result populates `_COVER_LAYOUT` in `report_builder.py`, which cover-page helpers read via `_cl(key, default)`.

### Data Models (`app/session.py`)

- `ReportMeta` — project metadata (site, client, dates, report type)
- `SystemEntry` — one BMP/stormwater system (type, ID, display name, condition)
- `WriteUp` — per-system text fields (findings, recommendations, maintenance_performed, post_service_condition)
- `Photo` — Full Report photo with computed caption logic in `computed_caption()`
- `PhotosheetPhoto` — Photosheet photo with component-based caption fields (caption_id, caption_view, caption_note)
- `ProjectSession` — root container: meta + systems[] + write_ups{entry_id: WriteUp} + photos[]

### Domain Constants (`app/constants.py`)

Two sets of constants for the two workflows:
- Full Report: `SYSTEM_TYPES`, `SYSTEM_ID_PREFIX`, `COMPONENT_OPTIONS`, `get_components_for_system()`, write-up template functions
- Photosheet: `PS_SYSTEM_TYPES` (ordered by stormwater flow convention for auto-sort), `PS_VIEW_TYPES`, `PS_COMPONENTS`, `PS_LAYOUTS`, `PS_VIEW_PRIORITY` (used for within-system ordering), `PS_SYSTEM_ORDER` (used for cross-system auto-sort)

Add new system types or components here to extend the domain vocabulary.

### Style Constants

`STYLE_CONFIG` in `report_builder.py` is the single source of truth for DOCX styling (font, sizes, colors). Sterling brand color is `#1AB738` (maintenance green), stored as `_STERLING_GREEN`. The logo is loaded from `assets/sterling_logo.png` relative to the builder file.

Photo grid layouts in the Full Report are configured in `_GRID_CFG` (keys: `"2x2"`, `"2x3"`, `"3x3"`) with per-grid column widths and max heights. Photosheet layouts use `PS_LAYOUTS` in `constants.py`.

### Photo Handling

- Photos uploaded in Full Report are copied to `projects/{project_id}/photos/` by `app/services/photo_service.py`, which also handles EXIF-aware orientation correction.
- Thumbnail cache lives in `st.session_state.ps_thumb_bytes` (photosheet) or `st.session_state.photo_bytes` (full report).
- `resize_for_report()` in `photo_service.py` is called during DOCX export to resize photos before embedding.
- `_get_display_size()` in `report_builder.py` computes constrained display dimensions (width × height) to prevent portrait photos from overflowing grid cells.

### Photosheet Caption Sync

Before export, `ps_sync_widget_states()` in `session.py` must be called to flush pending Streamlit widget state (caption fields, notes) back into `PhotosheetPhoto` objects and rebuild the combined `caption` string from its components (`system`, `caption_id`, `caption_view`, `caption_note` joined by ` – `).

## Key File Locations

| Purpose | File |
|---------|------|
| App entry point & mode router | `stormwater_app/app.py` |
| All data models & session helpers | `stormwater_app/app/session.py` |
| Domain constants (system types, views, layouts) | `stormwater_app/app/constants.py` |
| Full Report DOCX builder | `stormwater_app/app/services/report_builder.py` |
| Photosheet DOCX builder | `stormwater_app/app/services/photosheet_builder.py` |
| Cover page fit algorithm | `stormwater_app/app/services/page_fit.py` |
| Photo resizing & EXIF correction | `stormwater_app/app/services/photo_service.py` |
| Sterling brand styles (CSS injection) | `stormwater_app/app/components/styles.py` |
| Logo asset | `stormwater_app/assets/sterling_logo.png` |

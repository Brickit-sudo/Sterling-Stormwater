"""
app/services/bulk_importer.py
Parse imported PDF/DOCX report text into knowledge base rows,
then append them to the Excel knowledge base file.
"""

from __future__ import annotations
import re
from pathlib import Path

# Map heading keywords → canonical SYSTEM_TYPES value
_HEADING_SYSTEM_MAP = {
    "bioretention":           "Bioretention Cell",
    "catch basin":            "Catch Basin / Inlet",
    "inlet":                  "Catch Basin / Inlet",
    "constructed wetland":    "Constructed Wetland",
    "dry swale":              "Dry Swale",
    "extended detention":     "Extended Detention Basin",
    "grass channel":          "Grass Channel",
    "green roof":             "Green Roof",
    "infiltration basin":     "Infiltration Basin",
    "infiltration trench":    "Infiltration Trench",
    "level spreader":         "Level Spreader",
    "sand filter":            "Media Filter / Sand Filter",
    "media filter":           "Media Filter / Sand Filter",
    "oil water separator":    "Oil / Water Separator",
    "oil/water":              "Oil / Water Separator",
    "permeable pavement":     "Permeable Pavement",
    "proprietary":            "Proprietary Treatment Device",
    "retention pond":         "Retention Pond",
    "riprap":                 "Riprap Outfall Protection",
    "stormwater wetland":     "Stormwater Wetland",
    "underdrain soil filter": "Underdrain Soil Filter",
    "underdrain":             "Underdrain Soil Filter",
    "underground detention":  "Underground Detention",
    "vegetated filter":       "Vegetated Filter Strip",
    "filter strip":           "Vegetated Filter Strip",
    "wet pond":               "Wet Pond",
    "wet detention":          "Wet Pond",
}

# Map section heading → KB field name
_SECTION_TO_FIELD: dict[str, str] = {
    "findings":               "findings",
    "inspection findings":    "findings",
    "inspection summary":     "findings",
    "recommendations":        "recommendations",
    "recommendation":         "recommendations",
    "maintenance performed":  "maintenance_performed",
    "maintenance summary":    "maintenance_performed",
    "maintenance":            "maintenance_performed",
    "post service condition": "post_service_condition",
    "post service":           "post_service_condition",
    "post-service":           "post_service_condition",
    "follow-up":              "post_service_condition",
    "follow up":              "post_service_condition",
}

_SUMMARY_PATTERNS = [
    "inspection summary",
    "maintenance summary",
    "inspection and maintenance summary",
    "site description",
    "summary and findings",
    "overall summary",
]

_CONDITION_KEYWORDS: dict[str, list[str]] = {
    "Good": [
        "good condition", "excellent condition", "no deficiencies",
        "functioning properly", "no issues", "well-maintained",
        "no significant issues", "in good",
    ],
    "Fair": [
        "fair condition", "minor deficiencies", "maintenance recommended",
        "some sediment", "minor sediment", "some debris", "minor erosion",
    ],
    "Poor": [
        "poor condition", "significant deficiencies", "immediate attention",
        "major deficiencies", "failing", "severely clogged", "heavily sediment",
    ],
}


def _detect_system_type(heading: str) -> str | None:
    h = heading.lower()
    for keyword, system_type in _HEADING_SYSTEM_MAP.items():
        if keyword in h:
            return system_type
    return None


def _detect_field(heading: str) -> str | None:
    h = heading.lower().strip()
    for key, field in _SECTION_TO_FIELD.items():
        if key in h:
            return field
    return None


def _detect_condition(text: str) -> str:
    t = text.lower()
    for condition, keywords in _CONDITION_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return condition
    return "ALL"


def _is_summary_section(heading: str) -> bool:
    h = heading.lower()
    return any(p in h for p in _SUMMARY_PATTERNS)


def _section_pos(raw_text: str, heading: str) -> int:
    try:
        return raw_text.index(heading)
    except ValueError:
        return 999_999


def extract_kb_rows(
    raw_text: str,
    sections: dict,
    report_type: str = "ALL",
    source_label: str = "",
) -> dict:
    """
    Parse a report's raw_text + sections dict (from importer.py) into KB rows.

    Returns:
      {
        "writeups":  [{"system_type", "condition", "field", "label", "text"}, ...],
        "summaries": [{"report_type", "label", "text"}, ...],
        "captions":  [{"system_type", "view", "label", "caption"}, ...],
      }
    """
    from app.services.importer import extract_photo_captions

    writeups:  list[dict] = []
    summaries: list[dict] = []

    # Sort sections by position in raw text to preserve heading order
    ordered = sorted(
        sections.items(),
        key=lambda kv: _section_pos(raw_text, kv[0]),
    )

    current_system: str | None = None

    for heading, text in ordered:
        text = (text or "").strip()
        if len(text) < 30:
            continue

        slug = f"{source_label} — " if source_label else ""

        # ── Summary sections ──────────────────────────────────────────────────
        if _is_summary_section(heading):
            summaries.append({
                "report_type": report_type,
                "label":       f"{slug}{heading}",
                "text":        text,
            })
            continue

        # ── System-type heading → default to "findings" field ─────────────────
        sys_type = _detect_system_type(heading)
        if sys_type:
            current_system = sys_type
            condition = _detect_condition(text)
            writeups.append({
                "system_type": sys_type,
                "condition":   condition,
                "field":       "findings",
                "label":       f"{slug}{sys_type}",
                "text":        text,
            })
            continue

        # ── Field-type heading (Findings, Recommendations, etc.) ──────────────
        field = _detect_field(heading)
        if field:
            target_sys = current_system or "ALL"
            condition  = _detect_condition(text)
            writeups.append({
                "system_type": target_sys,
                "condition":   condition,
                "field":       field,
                "label":       f"{slug}{target_sys} — {heading}",
                "text":        text,
            })

    # ── Photo captions ────────────────────────────────────────────────────────
    captions: list[dict] = []
    for cap in extract_photo_captions(raw_text):
        st_val  = cap.get("system_type") or "ALL"
        view    = cap.get("view")        or ""
        sid     = cap.get("system_id")   or ""
        label   = f"{source_label} — {st_val} {sid}".strip(" —") if source_label else f"{st_val} {sid}".strip()
        caption = " – ".join(filter(None, [st_val, sid, view]))
        captions.append({
            "system_type": st_val,
            "view":        view,
            "label":       label,
            "caption":     caption,
        })

    return {"writeups": writeups, "summaries": summaries, "captions": captions}


def append_rows_to_kb(
    writeup_rows:  list[dict],
    summary_rows:  list[dict],
    caption_rows:  list[dict],
    kb_path: Path | None = None,
) -> tuple[int, int, int]:
    """
    Append selected rows to the knowledge base Excel file.
    Returns (n_writeups_added, n_summaries_added, n_captions_added).
    Raises FileNotFoundError if kb_path does not exist.
    """
    import openpyxl

    if kb_path is None:
        kb_path = Path("assets/knowledge_base.xlsx")

    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {kb_path}")

    wb = openpyxl.load_workbook(str(kb_path))

    def _append(sheet_name: str, rows: list[list]) -> int:
        if sheet_name not in wb.sheetnames or not rows:
            return 0
        ws = wb[sheet_name]
        for row in rows:
            ws.append(row)
        return len(rows)

    wu_added  = _append("WriteUps", [
        [r["system_type"], r["condition"], r["field"], r["label"], r["text"]]
        for r in writeup_rows
    ])
    sum_added = _append("SummaryTemplates", [
        [r["report_type"], r["label"], r["text"]]
        for r in summary_rows
    ])
    cap_added = _append("PhotoCaptions", [
        [r["system_type"], r["view"], r["label"], r["caption"]]
        for r in caption_rows
    ])

    wb.save(str(kb_path))
    wb.close()
    return wu_added, sum_added, cap_added

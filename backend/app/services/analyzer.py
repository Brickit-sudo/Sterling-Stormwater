"""
backend/app/services/analyzer.py
Structured analysis engine for Sterling stormwater inspection reports.

Returns a ReportAnalysis with four primary categories:
  1. site_info    — all header fields (name, address, dates, inspector, etc.)
  2. systems      — per-system findings, recommendations, condition
  3. photo_captions — structured caption list usable to seed the next report
  4. recommendations — standalone numbered list
  5. introduction — site description / background text
  6. sections     — all named text sections (raw)
"""

import re
from app.services.importer import extract_text_from_bytes, extract_fields, extract_photo_captions

# ── Known system types (mirrors constants.py in the Streamlit app) ────────────
SYSTEM_TYPES = [
    "Bioretention Cell", "Catch Basin / Inlet", "Constructed Wetland",
    "Dry Swale", "Extended Detention Basin", "Grass Channel", "Green Roof",
    "Infiltration Basin", "Infiltration Trench", "Level Spreader",
    "Media Filter / Sand Filter", "Oil / Water Separator", "Permeable Pavement",
    "Proprietary Treatment Device", "Retention Pond", "Riprap Outfall Protection",
    "Stormwater Wetland", "Underdrain Soil Filter", "Underground Detention",
    "Vegetated Filter Strip", "Wet Pond", "Other / Custom",
]

_FINDINGS_KEYS  = ["findings", "summary", "inspection findings", "maintenance summary",
                   "inspection summary", "inspection and maintenance"]
_REC_KEYS       = ["recommendation"]
_INTRO_KEYS     = ["introduction", "site description", "background", "scope"]


def _match_system_type(raw_type: str) -> str:
    """Fuzzy-match an extracted type string to the nearest known SYSTEM_TYPES entry."""
    raw_lower = raw_type.lower()
    for st in SYSTEM_TYPES:
        if st.lower() in raw_lower or raw_lower in st.lower():
            return st
    # Word overlap fallback
    raw_words = set(raw_lower.split())
    best, best_score = "Other / Custom", 0
    for st in SYSTEM_TYPES:
        overlap = len(raw_words & set(st.lower().split()))
        if overlap > best_score:
            best, best_score = st, overlap
    return best if best_score > 0 else raw_type


def _extract_intro(sections: dict) -> str:
    for key, text in sections.items():
        if any(k in key.lower() for k in _INTRO_KEYS):
            return text.strip()
    return ""


def _extract_recommendations_list(sections: dict) -> list[str]:
    """Pull recommendations section into a clean list."""
    rec_text = ""
    for key, text in sections.items():
        if any(k in key.lower() for k in _REC_KEYS):
            rec_text = text
            break
    if not rec_text:
        return []

    # Try numbered items: "1." "1)" "a."
    items = re.findall(
        r"^\s*(?:\d+|[a-z])[.)]\s+(.+?)(?=\n\s*(?:\d+|[a-z])[.)]|\Z)",
        rec_text, re.MULTILINE | re.DOTALL,
    )
    if items:
        return [i.strip() for i in items if i.strip()]

    # Try bullet items
    items = re.findall(r"^\s*[-•●◦▪]\s*(.+?)$", rec_text, re.MULTILINE)
    if items:
        return [i.strip() for i in items if i.strip()]

    # Fall back: non-empty lines
    return [l.strip() for l in rec_text.splitlines() if l.strip()]


def _split_findings_by_system(findings_text: str, captions: list[dict]) -> dict[str, str]:
    """
    Split a findings/summary block into per-system text keyed by system_id.
    Looks for lines that contain a known system ID or system name as a header.
    Returns: {system_id: findings_text}
    """
    if not captions:
        return {}

    # Build lookup: (system_id, system_type, display_name variants)
    systems = []
    for c in captions:
        sid = c["system_id"].upper()
        stype = c["system_type"]
        systems.append({
            "id": sid,
            "type": stype,
            "patterns": [
                re.escape(sid),
                re.escape(stype),
                re.escape(stype.split()[0]) if stype else "",  # first word e.g. "Bioretention"
            ]
        })

    lines = findings_text.split("\n")
    result: dict[str, list] = {s["id"]: [] for s in systems}
    current_id = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_id:
                result[current_id].append("")
            continue

        # Detect system header line: contains known ID and is short / ends with colon
        matched_id = None
        for s in systems:
            for pat in s["patterns"]:
                if pat and re.search(pat, stripped, re.IGNORECASE):
                    # Extra guard: line must be short (header) or end with colon
                    if len(stripped) < 80 or stripped.endswith(":"):
                        matched_id = s["id"]
                        break
            if matched_id:
                break

        if matched_id:
            current_id = matched_id
        elif current_id:
            result[current_id].append(stripped)

    # Clean up
    return {
        sid: "\n".join(lines).strip()
        for sid, lines in result.items()
        if any(l.strip() for l in lines)
    }


def _build_systems(captions: list[dict], findings_by_id: dict, recs_by_id: dict) -> list[dict]:
    """Build per-system analysis objects from captions + extracted text."""
    seen: set = set()
    systems = []
    for cap in sorted(captions, key=lambda c: c.get("order", 0)):
        sid = cap["system_id"].upper()
        if sid in seen:
            continue
        seen.add(sid)
        matched_type = _match_system_type(cap["system_type"])
        systems.append({
            "system_id":   sid,
            "system_type": matched_type,
            "display_name": f"{matched_type} {sid}",
            "findings":    findings_by_id.get(sid, ""),
            "recommendations": recs_by_id.get(sid, ""),
            "condition":   None,   # not extractable from text alone
        })
    return systems


def analyze_report(filename: str, file_bytes: bytes) -> dict:
    """
    Full structured analysis of a Sterling inspection report.
    Returns a ReportAnalysis dict.
    """
    extracted = extract_text_from_bytes(filename, file_bytes)
    raw_text  = extracted.get("raw_text", "")
    sections  = extracted.get("sections", {})

    # Use pre-extracted captions from structural parsing; fall back to regex only
    # if the structural pass found nothing (e.g. very old/unusual format)
    pre_caps = extracted.get("_captions")           # list or None
    cover    = extracted.get("_cover", {})

    fields   = extract_fields(raw_text)
    captions = extract_photo_captions(raw_text, pre_extracted=pre_caps if pre_caps else None)

    # Supplement extract_fields with cover table data when regex misses things
    if cover:
        for label, value in cover.items():
            lbl = label.lower()
            if not fields["site_name"] and ("site name" in lbl or "site:" == lbl):
                fields["site_name"] = value.split(" - ")[0].strip() if " - " in value else value
            if not fields["site_address"] and "address" in lbl:
                fields["site_address"] = value
            if not fields["prepared_by"] and ("prepared by" in lbl or "performed by" in lbl):
                fields["prepared_by"] = value
            if not fields["inspection_date"] and "date" in lbl:
                # Only capture if it looks like a date
                if re.search(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\w+ \d{1,2},?\s+\d{4}", value):
                    fields["inspection_date"] = value

    # ── Per-system findings from findings sections ────────────────────────────
    findings_text = "\n\n".join(
        text for key, text in sections.items()
        if any(k in key.lower() for k in _FINDINGS_KEYS)
    )
    findings_by_id = _split_findings_by_system(findings_text, captions)

    # Per-system recommendations (from recommendations section, split same way)
    rec_text = "\n\n".join(
        text for key, text in sections.items()
        if any(k in key.lower() for k in _REC_KEYS)
    )
    recs_by_id = _split_findings_by_system(rec_text, captions)

    # ── Site info ─────────────────────────────────────────────────────────────
    site_info = {
        "site_name":       fields.get("site_name", ""),
        "site_address":    fields.get("site_address", ""),
        "prepared_by":     fields.get("prepared_by", ""),
        "inspection_date": fields.get("inspection_date", ""),
        "report_type":     fields.get("report_type", ""),
        "system_types":    fields.get("system_types", []),
        "raw_summary":     fields.get("raw_summary", ""),
    }

    return {
        "site_info":       site_info,
        "systems":         _build_systems(captions, findings_by_id, recs_by_id),
        "photo_captions":  captions,
        "recommendations": _extract_recommendations_list(sections),
        "introduction":    _extract_intro(sections),
        "sections":        sections,
        "error":           extracted.get("error"),
    }

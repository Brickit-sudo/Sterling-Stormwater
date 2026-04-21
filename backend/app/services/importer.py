"""
backend/app/services/importer.py
Text extraction and structured parsing for Sterling stormwater inspection reports.

Handles two report generations:
  • Old Sterling PDF  — cover table + 3-col findings table + photo pages with
                        (N) (M) number rows followed by side-by-side caption text
  • New app DOCX/PDF  — section-header tables + inline paragraphs + 2-col photo
                        caption tables (or same-line caption pairs in the PDF render)

Returns a dict with:
  raw_text     — plain text (for legacy extract_fields fallback)
  sections     — {section_name: body_text}
  page_count   — int or "N/A (DOCX)"
  _captions    — pre-extracted list[dict] (use this instead of regex on raw_text)
  _cover       — {field_label: value} from the cover / general-info table
"""

import io
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Known section heading keywords (all lowercase)
# ---------------------------------------------------------------------------
_HEADING_KW = [
    "general information", "introduction", "background", "scope of work",
    "scope of services", "summary", "inspection summary", "maintenance summary",
    "summary and findings", "findings and recommendations",
    "inspection findings", "inspection and maintenance",
    "stormwater inspection findings",
    "recommendations", "photo documentation",
    "service photos", "certification",
    "site description",
]

# Abbreviation → system_type mapping for caption ID generation
_TYPE_ABBREV: dict[str, str] = {
    "BC":  "Bioretention Cell",
    "CB":  "Catch Basin / Inlet",
    "USF": "Underdrained Soil Filter",
    "GC":  "Grass Channel",
    "WP":  "Wet Pond",
    "RP":  "Retention Pond",
    "SW":  "Stormwater Wetland",
    "EDB": "Extended Detention Basin",
    "PP":  "Permeable Pavement",
    "GR":  "Green Roof",
    "LS":  "Level Spreader",
    "MF":  "Media Filter / Sand Filter",
    "OWS": "Oil / Water Separator",
    "IB":  "Infiltration Basin",
    "IT":  "Infiltration Trench",
    "UG":  "Underground Detention",
    "VFS": "Vegetated Filter Strip",
    "DS":  "Dry Swale",
    "CW":  "Constructed Wetland",
    "RO":  "Riprap Outfall Protection",
}

# Reverse: type words → abbreviation prefix  (first significant words)
_TYPE_TO_PREFIX: dict[str, str] = {
    "bioretention":    "BC",
    "catch basin":     "CB",
    "inlet":           "CB",
    "underdrain":      "USF",
    "usf":             "USF",
    "grass channel":   "GC",
    "grass":           "GC",
    "wet pond":        "WP",
    "retention pond":  "RP",
    "stormwater wetl": "SW",
    "extended deten":  "EDB",
    "permeable":       "PP",
    "green roof":      "GR",
    "level spread":    "LS",
    "media filter":    "MF",
    "sand filter":     "MF",
    "oil":             "OWS",
    "infiltration bas": "IB",
    "infiltration tre": "IT",
    "underground":     "UG",
    "vegetated":       "VFS",
    "dry swale":       "DS",
    "constructed wet": "CW",
    "riprap":          "RO",
    "misc drainage":   "DA",
    "drainage area":   "DA",
    "conveyance":      "CP",
    "pipe":            "CP",
}


# ===========================================================================
# Public API
# ===========================================================================

def extract_text_from_path(file_path: str) -> dict:
    path = Path(file_path)
    try:
        file_bytes = path.read_bytes()
        return extract_text_from_bytes(path.name, file_bytes)
    except Exception as e:
        return _empty(str(e))


def extract_text_from_bytes(filename: str, file_bytes: bytes) -> dict:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            return _extract_pdf(file_bytes)
        elif suffix == ".docx":
            return _extract_docx(file_bytes)
        else:
            return _empty(f"Unsupported file type: {suffix}")
    except Exception as e:
        return _empty(str(e))


def extract_fields(raw_text: str) -> dict:
    """Legacy field extractor — reads raw_text.  Still used by analyzer.py."""
    result = {
        "site_name": "", "site_address": "", "prepared_by": "",
        "inspection_date": "", "report_type": "", "system_types": [], "raw_summary": "",
    }
    if not raw_text:
        return result

    # Report type
    if re.search(r"inspection\s+and\s+maintenance\s+report", raw_text, re.IGNORECASE):
        result["report_type"] = "Inspection and Maintenance"
    elif re.search(r"maintenance\s+report", raw_text, re.IGNORECASE):
        result["report_type"] = "Maintenance"
    elif re.search(r"inspection\s+report", raw_text, re.IGNORECASE):
        result["report_type"] = "Inspection"
    elif re.search(r"compliance\s+report", raw_text, re.IGNORECASE):
        result["report_type"] = "Compliance"

    _NF = (r"(?=\s*(?:Number\s*(?:&|and)?\s*Type\b|Inspection\s+Performed\s+By\b"
           r"|Number\s+of\s+Pages\b|Report\s+Prepared\s+By\b|Inspection\s+Company\b"
           r"|Stormwater\s+Compliance|\n|\Z))")

    for pat in [
        r"Site\s+Name\s*(?:&|and)?\s*Location\s*:\s*(.+?)" + _NF,
        r"Site\s+Name\s*:\s*(.+?)(?=\s+Address\s*:|" + _NF + ")",
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            full_value = m.group(1).strip().rstrip(",")
            dash_split = re.split(r"\s+-\s+", full_value, maxsplit=1)
            if len(dash_split) == 2:
                result["site_name"]    = dash_split[0].strip()
                result["site_address"] = dash_split[1].strip()
            else:
                result["site_name"] = full_value
            break

    # Address on same line
    if not result["site_address"]:
        m = re.search(r"Address\s*:\s*(.+?)(?:\n|\Z)", raw_text, re.IGNORECASE)
        if m:
            result["site_address"] = m.group(1).strip()

    _PG = (r"(?=\s*(?:Number\s+of\s+Pages\b|Number\s*(?:&|and)?\s*Type\b"
           r"|\(\d+\)\s+[A-Z]|\n|\Z))")
    for label_pat in [
        r"Inspection\s+Performed\s+By\s*:\s*(.+?)" + _PG,
        r"Performed\s+By\s*:\s*(.+?)" + _PG,
        r"Report\s+Prepared\s+By\s*:\s*(.+?)" + _PG,
        r"Prepared\s+By\s*:\s*(.+?)" + _PG,
    ]:
        m = re.search(label_pat, raw_text, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            value = re.sub(r"\s*\((?:LCWMD\s+BMP#?\s*\d+[-\w]*|BMP#?\s*\d+[-\w]*)\)\s*$",
                           "", value, flags=re.IGNORECASE).strip()
            value = re.split(r"\s+Stormwater\s+Compliance", value, flags=re.IGNORECASE)[0].strip()
            if value:
                result["prepared_by"] = value
                break

    for pat in [
        r"performed\s+on\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        r"performed\s+on\s+(\w+\s+\d{1,2},?\s+\d{4})",
        r"Inspection\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"Inspection\s+Date\s*:\s*(\w+\s+\d{1,2},?\s+\d{4})",
        r"Date\s*:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"Date\s*:\s*(\w+\s+\d{1,2},?\s+\d{4})",
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            result["inspection_date"] = m.group(1).strip()
            break

    return result


def extract_photo_captions(raw_text: str, pre_extracted: list | None = None) -> list[dict]:
    """
    Return photo caption dicts.  If pre_extracted is provided (from structural
    parsing), return those directly instead of running the regex.
    """
    if pre_extracted is not None:
        return pre_extracted

    if not raw_text:
        return []

    captions: list[dict] = []
    seen: set = set()

    # ── Format 1: "(N) text (M) text" on a single line (new PDF render) ──────
    for line in raw_text.splitlines():
        if not re.search(r'\(\d+\)', line):
            continue
        for m in re.finditer(r'\((\d+)\)\s+(.+?)(?=\s*\(\d+\)|\s*$)', line):
            order = int(m.group(1))
            cap_text = m.group(2).strip()
            if cap_text and order not in seen:
                seen.add(order)
                captions.append(_parse_caption_text(order, cap_text))

    if captions:
        return sorted(captions, key=lambda c: c["order"])

    # ── Format 2: old style  "(N) SystemType – SID – View"  per line ─────────
    _SEP = r"\s*[–\-—]\s*"
    _ID  = r"([A-Z]{1,6}-\d{1,4}[A-Z]?)"
    old_pat = re.compile(
        r"^\s*\((\d+)\)\s+(.+?)" + _SEP + _ID + r"(?:" + _SEP + r"(.+?))?$",
        re.MULTILINE,
    )
    for m in old_pat.finditer(raw_text):
        order = int(m.group(1))
        if order in seen:
            continue
        seen.add(order)
        system_type = m.group(2).strip()
        system_id   = m.group(3).strip().upper()
        view        = (m.group(4) or "").strip()
        captions.append({
            "order":        order,
            "system_type":  system_type,
            "system_id":    system_id,
            "display_name": f"{system_type} ({system_id})",
            "view":         view,
        })

    return sorted(captions, key=lambda c: c["order"])


# ===========================================================================
# Internal helpers
# ===========================================================================

def _empty(error: str = "") -> dict:
    return {"raw_text": "", "sections": {}, "page_count": 0,
            "_captions": [], "_cover": {}, "error": error}


# ---------------------------------------------------------------------------
# Caption text parser
# ---------------------------------------------------------------------------

def _type_to_prefix(raw_type: str) -> str:
    """Return a 2-4 char abbreviation for a system type string."""
    low = raw_type.lower()
    for key, prefix in _TYPE_TO_PREFIX.items():
        if key in low:
            return prefix
    # Fallback: initials of first two significant words
    words = [w for w in re.split(r"[\s/]+", raw_type) if len(w) > 2]
    if words:
        return "".join(w[0].upper() for w in words[:2])
    return "SYS"


def _parse_caption_text(order: int, text: str) -> dict:
    """
    Parse a caption string like:
      "Bioretention Cell 1 - Overall View - View 1"
      "USF 1 - View Of Inlet"
      "Catch Basin - Example 1 - Inside View"
      "Site Signage"
    Returns a caption dict with system_type, system_id, display_name, view.
    """
    text = text.strip()

    # Split on first " - " to separate display_name from view
    parts = re.split(r"\s+[–\-—]\s+", text, maxsplit=1)
    display_name = parts[0].strip()
    view         = parts[1].strip() if len(parts) > 1 else ""

    # Try to extract trailing number from display_name
    m = re.match(r"^(.+?)\s+(\d+)$", display_name)
    if m:
        type_part = m.group(1).strip()
        number    = m.group(2)
    else:
        type_part = display_name
        number    = "1"

    prefix    = _type_to_prefix(type_part)
    system_id = f"{prefix}-{number}"

    return {
        "order":        order,
        "system_type":  type_part,
        "system_id":    system_id,
        "display_name": display_name,
        "view":         view,
    }


# ---------------------------------------------------------------------------
# Section heading detector
# ---------------------------------------------------------------------------

def _is_heading(line: str) -> str | None:
    """Return normalized heading string if `line` looks like a section heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return None
    low = stripped.lower()

    # Keyword match
    for kw in _HEADING_KW:
        if kw in low:
            # Remove leading numbers/punctuation
            clean = re.sub(r"^[\d\.\s]+", "", stripped).strip()
            clean = re.sub(r":$", "", clean).strip()
            return clean or stripped

    # All-caps heuristic (3+ chars, not starting with a digit)
    if (stripped.isupper() and len(stripped) >= 3
            and not stripped[0].isdigit()
            and stripped not in ("LLC", "INC", "USA", "BMP")):
        return stripped.title()

    return None


# ---------------------------------------------------------------------------
# DOCX extractor — walks body elements in document order
# ---------------------------------------------------------------------------

def _extract_docx(file_bytes: bytes) -> dict:
    try:
        from docx import Document
        from docx.oxml.ns import qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table, _Cell
    except ImportError:
        return _empty("python-docx not installed")

    doc   = Document(io.BytesIO(file_bytes))
    W_P   = qn("w:p")
    W_TBL = qn("w:tbl")

    sections: dict[str, list[str]] = {}
    captions: list[dict] = []
    cover: dict = {}
    current_section: str | None = None
    buffer: list[str] = []
    cover_done = False

    def _flush():
        nonlocal buffer
        if current_section and buffer:
            body = "\n".join(l for l in buffer if l.strip()).strip()
            if body:
                if current_section in sections:
                    sections[current_section] += "\n" + body
                else:
                    sections[current_section] = body
        buffer = []

    def _cell_text(cell) -> str:
        return "\n".join(p.text for p in cell.paragraphs).strip()

    def _row_texts(row) -> list[str]:
        seen_texts: set = set()
        result = []
        for cell in row.cells:
            t = _cell_text(cell)
            if t and t not in seen_texts:
                seen_texts.add(t)
                result.append(t)
        return result

    for block in doc.element.body:
        tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

        # ── Paragraph ────────────────────────────────────────────────────────
        if tag == "p":
            para = Paragraph(block, doc)
            text = para.text.strip()
            if not text:
                continue
            heading = _is_heading(text)
            if heading and para.style.name.lower() in (
                "heading 1", "heading 2", "heading 3", "title",
            ):
                _flush()
                current_section = heading
            elif text and current_section is not None:
                buffer.append(text)

        # ── Table ─────────────────────────────────────────────────────────────
        elif tag == "tbl":
            tbl   = Table(block, doc)
            nrows = len(tbl.rows)
            ncols = len(tbl.columns) if nrows else 0

            # Single-cell table → section header
            if nrows == 1 and ncols == 1:
                cell_text = _cell_text(tbl.rows[0].cells[0])
                heading   = _is_heading(cell_text)
                if heading:
                    _flush()
                    current_section = heading
                    continue

            # Check any cell for "(N)" pattern → photo caption table
            # Photo rows come first with image (empty text); caption rows follow
            has_caption_cell = any(
                re.match(r"^\s*\(\d+\)", _cell_text(cell))
                for row in tbl.rows
                for cell in row.cells
            )
            if has_caption_cell:
                    seen_cap_orders: set = set()
                    for row in tbl.rows:
                        for cell in row.cells:
                            ct = _cell_text(cell).strip()
                            m  = re.match(r"^\s*\((\d+)\)\s+(.+)", ct, re.DOTALL)
                            if m:
                                order    = int(m.group(1))
                                cap_text = m.group(2).replace("\n", " ").strip()
                                if order not in seen_cap_orders and cap_text:
                                    seen_cap_orders.add(order)
                                    captions.append(_parse_caption_text(order, cap_text))
                    continue

            # Cover / general info table (first real table before any section)
            if not cover_done and not cover:
                for row in tbl.rows:
                    texts = _row_texts(row)
                    if len(texts) >= 2:
                        label = texts[0].rstrip(":").strip()
                        value = texts[1].strip()
                        if label and value and len(label) < 60:
                            cover[label] = value
                    elif len(texts) == 1:
                        # Might be a multi-line component list
                        t = texts[0]
                        if re.search(r"\(\d+\)", t):
                            cover["component_list"] = t
                if cover:
                    cover_done = True
                continue

            # Regular body table — add text to current section
            if current_section:
                for row in tbl.rows:
                    row_t = "  |  ".join(_row_texts(row))
                    if row_t.strip():
                        buffer.append(row_t)

    _flush()

    # Build raw_text: cover fields first, then sections
    cover_lines = [f"{k}: {v}" for k, v in cover.items() if k != "component_list"]
    if "component_list" in cover:
        cover_lines.append("Number & Type of Stormwater Components Inspected:")
        cover_lines.append(cover["component_list"])

    parts = ["\n".join(cover_lines)] if cover_lines else []
    for sec_name, sec_body in sections.items():
        parts.append(f"{sec_name.upper()}\n{sec_body}")
    raw_text = "\n\n".join(parts)

    # Sort captions
    captions = sorted({c["order"]: c for c in captions}.values(),
                      key=lambda c: c["order"])

    return {
        "raw_text":    raw_text,
        "sections":    sections,
        "page_count":  "N/A (DOCX)",
        "_captions":   captions,
        "_cover":      cover,
    }


# ---------------------------------------------------------------------------
# PDF extractor — pdfplumber with table + word-position extraction
# ---------------------------------------------------------------------------

def _extract_pdf(file_bytes: bytes) -> dict:
    try:
        import pdfplumber
    except ImportError:
        return _empty("pdfplumber not installed")

    captions: list[dict]  = []
    sections: dict        = {}
    cover: dict           = {}
    all_text_parts: list  = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            raw = page.extract_text() or ""

            # ── Cover page (page 0) ──────────────────────────────────────────
            if page_num == 0:
                cover = _parse_pdf_cover(page)
                # Build cover text for raw_text
                cover_lines = [f"{k}: {v}" for k, v in cover.items()
                               if k not in ("component_list",)]
                if "component_list" in cover:
                    cover_lines.append("Number & Type: " + cover["component_list"])
                all_text_parts.append("\n".join(cover_lines))
                # Also accumulate sections from page 1 text
                _accumulate_sections(raw, sections)
                continue

            # ── Photo page ───────────────────────────────────────────────────
            if "Service Photos Are Provided Below" in raw or re.search(
                r"^\s*\(\d+\)\s*\(\d+\)\s*$", raw, re.MULTILINE
            ):
                page_caps = _extract_pdf_photo_page(page)
                captions.extend(page_caps)
                continue

            # ── Findings/content page — try table extraction first ────────────
            tables = page.extract_tables()
            if tables:
                for tbl in tables:
                    _parse_findings_table(tbl, sections)

            _accumulate_sections(raw, sections)
            all_text_parts.append(raw)

    # Deduplicate captions by order
    seen_orders: set = set()
    unique_caps: list = []
    for cap in sorted(captions, key=lambda c: c["order"]):
        if cap["order"] not in seen_orders:
            seen_orders.add(cap["order"])
            unique_caps.append(cap)

    # Build raw_text
    sec_parts = [f"{name.upper()}\n{body}" for name, body in sections.items()]
    raw_text  = "\n\n".join(all_text_parts + sec_parts)

    return {
        "raw_text":   raw_text,
        "sections":   sections,
        "page_count": page_count,
        "_captions":  unique_caps,
        "_cover":     cover,
    }


def _parse_pdf_cover(page) -> dict:
    """Extract cover page fields using pdfplumber table extraction."""
    cover: dict = {}
    tables = page.extract_tables()
    for tbl in tables:
        if not tbl:
            continue
        for row in tbl:
            if not row:
                continue
            cells = [str(c).strip() if c else "" for c in row]
            # Look for "Label: Value" pattern in cells
            for i, cell in enumerate(cells):
                if not cell:
                    continue
                # Single cell with "Key: Value"
                m = re.match(r"^(.{3,50}?):\s+(.+)$", cell, re.DOTALL)
                if m:
                    cover[m.group(1).strip()] = m.group(2).strip().replace("\n", " ")
                # Two-cell row: cells[0] = label, cells[1] = value
                elif i == 0 and len(cells) >= 2 and cells[1]:
                    label = cell.rstrip(":").strip()
                    value = cells[1].strip().replace("\n", " ")
                    if label and value and len(label) < 60:
                        cover[label] = value
    return cover


def _extract_pdf_photo_page(page) -> list[dict]:
    """
    Extract photo captions from a photo page.

    Handles two layouts:
    1. Old Sterling PDF:  number row  →  "(1) (2)"
                          caption row →  "Caption A    Caption B"
    2. New app PDF:       inline      →  "(1) Caption A (2) Caption B"
    """
    words = page.extract_words(x_tolerance=5, y_tolerance=5)
    if not words:
        return []

    page_mid = (page.bbox[0] + page.bbox[2]) / 2

    # Group words by row (bucket top coordinate to nearest 4pt)
    row_map: dict[int, list] = {}
    for w in words:
        key = int(w["top"] / 4) * 4
        row_map.setdefault(key, []).append(w)

    captions: list[dict] = []
    pending_numbers: list[int] = []

    for y_key in sorted(row_map):
        row_words = sorted(row_map[y_key], key=lambda w: w["x0"])
        row_text  = " ".join(w["text"] for w in row_words).strip()

        # Skip header/footer lines
        if re.search(r"service photos|please contact|page \d+", row_text, re.IGNORECASE):
            continue

        # ── Old format: row contains only "(N)" tokens ─────────────────────
        stripped_for_num = re.sub(r"[\s()]", "", row_text)
        if stripped_for_num.isdigit() or re.fullmatch(r"[\d\s()]+", row_text):
            nums = [int(n) for n in re.findall(r"\((\d+)\)", row_text)]
            if nums:
                pending_numbers = nums
                continue

        # ── Old format: caption row following a number row ──────────────────
        if pending_numbers:
            if len(pending_numbers) == 1:
                captions.append(_parse_caption_text(pending_numbers[0], row_text))
            else:
                # Split by page midpoint
                left  = " ".join(w["text"] for w in row_words if w["x0"] <  page_mid).strip()
                right = " ".join(w["text"] for w in row_words if w["x0"] >= page_mid).strip()
                if left  and len(pending_numbers) >= 1:
                    captions.append(_parse_caption_text(pending_numbers[0], left))
                if right and len(pending_numbers) >= 2:
                    captions.append(_parse_caption_text(pending_numbers[1], right))
            pending_numbers = []
            continue

        # ── New format: "(N) text (M) text" on same line ────────────────────
        if re.search(r"\(\d+\)", row_text):
            for m in re.finditer(r"\((\d+)\)\s+(.+?)(?=\s*\(\d+\)|\s*$)", row_text):
                order    = int(m.group(1))
                cap_text = m.group(2).strip()
                if cap_text:
                    captions.append(_parse_caption_text(order, cap_text))

    return captions


def _parse_findings_table(tbl: list, sections: dict):
    """
    Parse a 3-column findings table (Component | Summary | Next Actions)
    from old-format PDFs and add entries to sections dict.
    """
    if not tbl or len(tbl) < 2:
        return
    # Detect header row
    header = [str(c or "").strip().lower() for c in tbl[0]]
    if not any("component" in h or "system" in h or "stormwater" in h for h in header):
        # Check second row
        if len(tbl) > 1:
            header = [str(c or "").strip().lower() for c in tbl[1]]
    if not any("summary" in h or "finding" in h for h in header):
        return  # Not a findings table

    findings_parts: list[str] = []
    recs_parts: list[str]     = []

    for row in tbl:
        cells = [str(c or "").strip() for c in row]
        if not any(cells):
            continue
        component = cells[0] if len(cells) > 0 else ""
        summary   = cells[1] if len(cells) > 1 else ""
        actions   = cells[2] if len(cells) > 2 else ""

        if component and component.lower() in ("stormwater\ncomponent", "stormwater component",
                                                "component", "summary", "next actions", ""):
            continue

        if component and summary:
            findings_parts.append(f"{component}\n{summary}")
        if component and actions:
            recs_parts.append(f"{component}: {actions}")

    if findings_parts:
        sec_key = "Inspection Findings"
        existing = sections.get(sec_key, "")
        sections[sec_key] = (existing + "\n\n" + "\n\n".join(findings_parts)).strip()
    if recs_parts:
        sec_key = "Recommendations"
        existing = sections.get(sec_key, "")
        sections[sec_key] = (existing + "\n\n" + "\n".join(recs_parts)).strip()


def _accumulate_sections(raw_text: str, sections: dict):
    """Parse section headings from raw text and accumulate into sections dict."""
    if not raw_text:
        return
    current: str | None = None
    buf: list[str]      = []

    def _flush_buf():
        if current and buf:
            body = "\n".join(l for l in buf if l.strip()).strip()
            if body:
                if current in sections:
                    sections[current] += "\n" + body
                else:
                    sections[current] = body

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = _is_heading(stripped)
        if heading and len(stripped) < 80:
            _flush_buf()
            current = heading
            buf = []
        elif current:
            buf.append(stripped)

    _flush_buf()

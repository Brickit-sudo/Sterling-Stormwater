"""
app/services/page_fit.py
═══════════════════════════════════════════════════════════════════════════════
Page-fit algorithm for Sterling Stormwater DOCX cover page.

PURPOSE
-------
The Sterling cover page must fit entirely on page 1: logo, title,
general-info table, intro text, findings, certification table, and footer.
Because python-docx has no browser-style layout engine, this module estimates
the vertical height of each content block from font metrics and applies staged
adjustments until the content fits — or reports which block(s) cause overflow.

UNITS
-----
All internal measurements are in POINTS (72 pt = 1 inch).

ESTIMATION MODEL
----------------
  chars_per_line  = usable_width_pt / (font_size_pt × char_width_factor)
  line_height_pt  = font_size_pt × line_height_factor
  block_height_pt = ceil(char_count / chars_per_line) × line_height_pt
                    + space_before_pt + space_after_pt

  char_width_factor  = 0.655  (calibrated for Calibri proportional spacing:
                                540pt width / 97 chars per line at 8.5pt = 5.57pt/char
                                → 5.57 / 8.5 = 0.655)
  line_height_factor = 1.20   (Word "single" spacing for Calibri)

STAGED ADJUSTMENTS (applied in order until content fits)
----------------------------------------------------------
  Stage 1  Strip nonessential whitespace (para spacing, spacers, cell padding)
  Stage 2  Zero bar cell before/after padding
  Stage 3  Scale body font down within safe range (default 8.5 pt → min 7.0 pt)
  Stage 4  Scale logo down within safe range (default 3.6" → min 2.5")
  Stage 5  Condense cert signature row spacing
  Stage 6  Flag overflow with offending block list — never silently break layout

INTEGRATION
-----------
  build_report() in report_builder.py calls apply_page_fit(proj) before
  building the cover page.  The returned PageFitResult.layout is serialized
  into _COVER_LAYOUT so cover-page helper functions use the adjusted values.

TESTING
-------
  Short content  (1-2 systems, brief text) → No adjustments needed
  Medium content (3-4 systems, ~200 chars each) → Stage 1 may apply
  Long content   (6+ systems, ~500 chars each) → Stage 2-3 likely needed
  Very long      (10+ systems) → Stage 3-4; Stage 6 may flag overflow
═══════════════════════════════════════════════════════════════════════════════
"""

import math
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ── Path to logo (needed for accurate height estimation) ──────────────────────
_LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "sterling_logo.png"

# ── Static text lengths (character count of fixed boilerplate) ────────────────
_INTRO_TEXT_LEN  = 556   # INTRODUCTION boilerplate paragraph
_CERT_TEXT_LEN   = 119   # CERTIFICATION boilerplate paragraph
_OPENER_TEXT_LEN = 140   # Findings opener sentence (estimated maximum)


# ══════════════════════════════════════════════════════════════════════════════
# Data models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PageLayout:
    """
    Single source of truth for all spacing / font-size parameters used when
    building the cover page.  Default values match the current Sterling template.
    apply_page_fit() returns a (possibly modified) copy of this object.
    Minimum thresholds (*_min_*) are guardrails — the algorithm never goes below them.
    """

    # ── Page geometry ──────────────────────────────────────────────────────────
    page_height_in:    float = 11.0
    page_width_in:     float = 8.5
    margin_top_in:     float = 0.61
    margin_bottom_in:  float = 0.50
    margin_side_in:    float = 0.50
    footer_height_in:  float = 0.0    # Word's footer renders inside the bottom margin,
                                       # NOT inside the body content area.  Subtracting it
                                       # here was wrong — it produced 682 pt available when
                                       # the true body height is 712 pt.  Set to 0 so
                                       # _available_height_pt() == BODY_HEIGHT_PT.

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_width_in:     float = 3.6
    logo_after_pt:     float = 4.0
    logo_width_min_in: float = 2.5    # Stage 4 guardrail

    # ── Report title ──────────────────────────────────────────────────────────
    title_size_pt:     float = 14.0
    title_before_pt:   float = 2.0
    title_after_pt:    float = 6.0
    title_size_min_pt: float = 11.0   # Stage 3 guardrail (titles only reduce slightly)

    # ── Green section bars ────────────────────────────────────────────────────
    bar_font_size_pt:  float = 10.0
    bar_before_pt:     float = 1.0
    bar_after_pt:      float = 1.0
    bar_spacer_pt:     float = 0.0    # blank paragraph AFTER bar (0 = already removed in Fix #1)
    bar_before_min_pt: float = 0.0
    bar_after_min_pt:  float = 0.0

    # ── Body text ─────────────────────────────────────────────────────────────
    body_size_pt:      float = 8.5
    body_before_pt:    float = 0.0
    body_after_pt:     float = 2.0
    body_size_min_pt:  float = 7.0    # Stage 3 guardrail

    # ── System subheadings (cover page compact versions) ──────────────────────
    subhead_before_pt:     float = 3.0
    subhead_after_pt:      float = 1.0
    subhead_before_min_pt: float = 0.0
    subhead_after_min_pt:  float = 0.0

    # ── Table cell vertical padding ───────────────────────────────────────────
    table_cell_pad_pt:     float = 1.0
    table_cell_pad_min_pt: float = 0.0

    # ── Cert signature row spacing ────────────────────────────────────────────
    cert_sig_before_pt:     float = 12.0
    cert_sig_after_pt:      float = 12.0
    cert_sig_before_min_pt: float = 2.0
    cert_sig_after_min_pt:  float = 2.0

    # ── Intro text ────────────────────────────────────────────────────────────
    intro_after_pt:     float = 2.0
    intro_after_min_pt: float = 0.0

    # ── Estimation constants ──────────────────────────────────────────────────
    # Calibri: avg char width = font_size × 0.655 pt  (empirically calibrated)
    char_width_factor:  float = 0.655
    # Word "single" line spacing for Calibri ≈ 1.20 × font size
    line_height_factor: float = 1.20


@dataclass
class ContentBlock:
    """One measured content block on the cover page."""
    name:        str
    height_pt:   float
    is_variable: bool = False    # True when height depends on user-entered content
    detail:      str  = ""       # human-readable note for debug output


@dataclass
class PageFitResult:
    """Result returned by apply_page_fit()."""
    fits:             bool
    used_pt:          float
    available_pt:     float
    overflow_pt:      float
    adjustments:      List[str]        = field(default_factory=list)
    offending_blocks: List[str]        = field(default_factory=list)
    layout:           Optional[object] = None    # PageLayout after adjustments
    blocks:           List[object]     = field(default_factory=list)  # ContentBlock list

    # ── Convenience accessors ─────────────────────────────────────────────────
    def used_in(self)      -> float: return self.used_pt      / 72.0
    def available_in(self) -> float: return self.available_pt / 72.0
    def overflow_in(self)  -> float: return self.overflow_pt  / 72.0

    def debug_summary(self) -> str:
        """Human-readable report of block heights, available space, and adjustments."""
        lines = [
            "─" * 62,
            f"Page fit: {'✓  FITS' if self.fits else '✗  OVERFLOW'}",
            f"  Used:       {self.used_in():.3f}\"  ({self.used_pt:.1f} pt)",
            f"  Available:  {self.available_in():.3f}\"  ({self.available_pt:.1f} pt)",
        ]
        if not self.fits:
            lines.append(
                f"  Overflow:   {self.overflow_in():.3f}\"  ({self.overflow_pt:.1f} pt)"
            )
        if self.adjustments:
            lines.append("  Adjustments:")
            for a in self.adjustments:
                lines.append(f"    · {a}")
        if self.offending_blocks:
            lines.append(f"  Offending blocks: {', '.join(self.offending_blocks)}")
        lines.append("  Block breakdown:")
        for b in self.blocks:
            tag = "  ← variable" if b.is_variable else ""
            detail = f"  [{b.detail}]" if b.detail else ""
            lines.append(
                f"    {b.name:<28s}  {b.height_pt:6.1f} pt{detail}{tag}"
            )
        lines.append("─" * 62)
        return "\n".join(lines)


# ── Single source of truth for page body height ───────────────────────────────
# Both page_fit.py AND report_builder.py import this constant so there is
# exactly one definition of the printable body height.
#
# Body height = page height − top margin − bottom margin.
# The footer lives in the bottom margin zone and does NOT consume body space;
# it is accounted for by footer_height_in = 0 in PageLayout.
#
# report_builder imports this as:
#   from app.services.page_fit import apply_page_fit, PageLayout, BODY_HEIGHT_PT
#   _BODY_HEIGHT_PT = BODY_HEIGHT_PT
_default_layout = PageLayout()
BODY_HEIGHT_PT = (
    _default_layout.page_height_in
    - _default_layout.margin_top_in
    - _default_layout.margin_bottom_in
) * 72.0   # (11.0 − 0.61 − 0.50) × 72 = 712.08 pt
del _default_layout


# ══════════════════════════════════════════════════════════════════════════════
# Estimation helpers
# ══════════════════════════════════════════════════════════════════════════════

def _usable_width_pt(layout: PageLayout) -> float:
    return (layout.page_width_in - 2.0 * layout.margin_side_in) * 72.0


def _available_height_pt(layout: PageLayout) -> float:
    return (
        layout.page_height_in    * 72.0
        - layout.margin_top_in    * 72.0
        - layout.margin_bottom_in * 72.0
        - layout.footer_height_in * 72.0
    )


def _logo_height_pt(layout: PageLayout) -> float:
    """
    Compute logo display height in points from the actual image aspect ratio.
    Falls back to Sterling logo's approximate aspect ratio (2.8 : 1) when PIL
    is unavailable or the image file is missing.
    """
    if _LOGO_PATH.exists():
        try:
            from PIL import Image
            img = Image.open(str(_LOGO_PATH))
            w_px, h_px = img.size
            aspect = w_px / max(h_px, 1)
            return (layout.logo_width_in / aspect) * 72.0
        except Exception:
            pass
    # Sterling logo fallback aspect ratio
    return (layout.logo_width_in / 2.8) * 72.0


def _text_height_pt(char_count: int,
                    font_size:   float,
                    usable_w_pt: float,
                    layout:      PageLayout,
                    before:      float,
                    after:       float) -> float:
    """
    Estimate the rendered height of a paragraph block in points.

    Model:
      chars_per_line = usable_width_pt / (font_size × char_width_factor)
      n_lines        = ceil(char_count / chars_per_line)
      height         = n_lines × (font_size × line_height_factor) + before + after

    Assumptions:
      - Plain prose text with normal word distribution
      - Calibri proportional spacing (char_width_factor = 0.655)
      - Word "single" line spacing (line_height_factor = 1.20)
    """
    if char_count <= 0:
        return 0.0
    chars_per_line = max(1.0, usable_w_pt / (font_size * layout.char_width_factor))
    n_lines = math.ceil(char_count / chars_per_line)
    return n_lines * (font_size * layout.line_height_factor) + before + after


def _bar_height_pt(layout: PageLayout) -> float:
    """Total height consumed by one green section bar (cell text + bar spacer)."""
    return (
        layout.bar_font_size_pt * layout.line_height_factor
        + layout.bar_before_pt
        + layout.bar_after_pt
        + layout.bar_spacer_pt
    )


def _findings_height_pt(proj, layout: PageLayout) -> float:
    """
    Estimate total height of the variable findings/summary block.
    Handles Inspection (opener + per-system findings/recs) and
    Maintenance/Combined (exec summary + per-system maintenance text).
    """
    usable_w = _usable_width_pt(layout)
    bs  = layout.body_size_pt
    rt  = proj.meta.report_type
    bp  = layout.body_before_pt
    ba  = layout.body_after_pt
    sp  = layout.subhead_before_pt
    sa  = layout.subhead_after_pt
    total = 0.0

    if rt == "Inspection":
        # Opener sentence
        total += _text_height_pt(_OPENER_TEXT_LEN, bs, usable_w, layout, bp, ba)
        for entry in proj.systems:
            wu = proj.write_ups.get(entry.entry_id)
            sub_chars = len(entry.display_name or entry.system_type)
            if entry.notes:
                sub_chars += len(entry.notes) + 3
            total += _text_height_pt(sub_chars, bs, usable_w, layout, sp, sa)
            for attr in ("findings", "recommendations"):
                t = getattr(wu, attr, "") if wu else ""
                if t:
                    total += _text_height_pt(len(t), bs, usable_w, layout, bp, ba)
    else:
        # Maintenance / Inspection and Maintenance
        exec_text = (
            getattr(proj.meta, "executive_summary", "")
            or proj.meta.site_description
            or ""
        )
        total += _text_height_pt(max(len(exec_text), 40), bs, usable_w, layout, bp, ba)
        for entry in proj.systems:
            wu = proj.write_ups.get(entry.entry_id)
            sub_chars = len(entry.display_name or entry.system_type)
            if entry.notes:
                sub_chars += len(entry.notes) + 3
            total += _text_height_pt(sub_chars, bs, usable_w, layout, sp, sa)
            attrs = []
            if rt == "Inspection and Maintenance":
                attrs.append("findings")
            attrs += ["maintenance_performed", "post_service_condition"]
            for attr in attrs:
                t = getattr(wu, attr, "") if wu else ""
                if t:
                    total += _text_height_pt(len(t), bs, usable_w, layout, bp, ba)

    return total


# ══════════════════════════════════════════════════════════════════════════════
# Block measurement
# ══════════════════════════════════════════════════════════════════════════════

def estimate_cover_blocks(proj, layout: PageLayout) -> List[ContentBlock]:
    """
    Measure every content block on the cover page.
    Returns a list of ContentBlock with height_pt set from the current layout values.
    Call this repeatedly with modified layouts to see how adjustments affect total height.
    """
    usable_w = _usable_width_pt(layout)
    bs  = layout.body_size_pt
    lhf = layout.line_height_factor
    cp  = layout.table_cell_pad_pt
    bar_h = _bar_height_pt(layout)
    blocks: List[ContentBlock] = []

    # ── 1. Logo ───────────────────────────────────────────────────────────────
    logo_h = _logo_height_pt(layout) + layout.logo_after_pt
    blocks.append(ContentBlock(
        "logo", logo_h,
        detail=f"{layout.logo_width_in:.2f}\" wide"
    ))

    # ── 2. Report title ───────────────────────────────────────────────────────
    title_h = (
        layout.title_size_pt * lhf
        + layout.title_before_pt
        + layout.title_after_pt
    )
    blocks.append(ContentBlock("title", title_h))

    # ── 3. GENERAL INFORMATION bar ────────────────────────────────────────────
    blocks.append(ContentBlock("bar_general_info", bar_h))

    # ── 4. Cover info table (3 rows left; right col shows BMP summary) ────────
    n_bmp = max(1, len(proj.systems))
    row_h   = bs * lhf + cp * 2
    left_h  = 3 * row_h
    # Right column: header label + one line per distinct system type
    n_types = max(1, len({s.system_type for s in proj.systems}))
    right_h = (bs * lhf + cp * 2) + n_types * bs * lhf
    table_h = max(left_h, right_h)
    blocks.append(ContentBlock(
        "cover_info_table", table_h, is_variable=True,
        detail=f"{n_bmp} system(s)"
    ))

    # ── 5. INTRODUCTION bar ───────────────────────────────────────────────────
    blocks.append(ContentBlock("bar_intro", bar_h))

    # ── 6. Intro boilerplate ──────────────────────────────────────────────────
    intro_h = _text_height_pt(
        _INTRO_TEXT_LEN, bs, usable_w, layout, 0.0, layout.intro_after_pt
    )
    blocks.append(ContentBlock(
        "intro_text", intro_h,
        detail=f"{_INTRO_TEXT_LEN} chars"
    ))

    # ── 7. Findings bar ───────────────────────────────────────────────────────
    blocks.append(ContentBlock("bar_findings", bar_h))

    # ── 8. Findings / summary content (variable) ─────────────────────────────
    findings_h = _findings_height_pt(proj, layout)
    blocks.append(ContentBlock(
        "findings_content", findings_h, is_variable=True,
        detail=f"{len(proj.systems)} system(s)"
    ))

    # ── 9. CERTIFICATION bar ──────────────────────────────────────────────────
    # Green section bar — same structure as all other bars.
    blocks.append(ContentBlock("bar_cert", bar_h))

    # ── 10. Certification table — 3-row structure matching report_builder ─────
    # Row 0: certification statement (full-width merged, ~2 lines of text)
    cert_row0_h = 2 * bs * lhf + 2 * cp
    # Row 1: Inspection Company / Report Prepared By / Cert Title (3 lines)
    cert_row1_h = 3 * bs * lhf + 2 * cp
    # Row 2: Signature row — spacing driven by cert_sig_before/after params
    cert_row2_h = (bs * lhf
                   + layout.cert_sig_before_pt
                   + layout.cert_sig_after_pt)
    # Border overhead: top + 2×insideH + bottom at sz=12, ≈1.5 pt each → 6 pt
    cert_border_h = 6.0
    cert_table_h  = cert_row0_h + cert_row1_h + cert_row2_h + cert_border_h
    blocks.append(ContentBlock(
        "cert_table", cert_table_h,
        detail=f"rows: {cert_row0_h:.1f}+{cert_row1_h:.1f}+{cert_row2_h:.1f}+border"
    ))

    # ── 11. Bottom green bar ──────────────────────────────────────────────────
    # Solid green footer bar: " " text at body size, before=2, after=2, borders ≈3pt
    bottom_bar_h = bs * lhf + 2.0 + 2.0 + 3.0   # line_h + before + after + borders
    blocks.append(ContentBlock("bottom_green_bar", bottom_bar_h))

    return blocks


# ══════════════════════════════════════════════════════════════════════════════
# Staged adjustment loop
# ══════════════════════════════════════════════════════════════════════════════

def _estimate_total_body_lines(proj, layout: PageLayout) -> int:
    """
    Count total estimated body text lines on the cover page.
    Used in Stage 3 to calculate how much height each point of font reduction saves.
    """
    usable_w = _usable_width_pt(layout)
    chars_per_line = max(
        1.0, usable_w / (layout.body_size_pt * layout.char_width_factor)
    )
    total_chars = _INTRO_TEXT_LEN + _CERT_TEXT_LEN + _OPENER_TEXT_LEN
    for entry in proj.systems:
        wu = proj.write_ups.get(entry.entry_id)
        total_chars += len(entry.display_name or entry.system_type)
        if wu:
            for attr in ("findings", "recommendations",
                         "maintenance_performed", "post_service_condition"):
                t = getattr(wu, attr, "") or ""
                total_chars += len(t)
    return math.ceil(total_chars / chars_per_line)


def _run_check(proj, layout: PageLayout):
    """Single measurement pass — returns (blocks, used_pt, avail_pt, overflow_pt)."""
    blocks  = estimate_cover_blocks(proj, layout)
    used_pt = sum(b.height_pt for b in blocks)
    avail   = _available_height_pt(layout)
    return blocks, used_pt, avail, max(0.0, used_pt - avail)


def apply_page_fit(proj) -> PageFitResult:
    """
    Main entry point.  Run the 6-stage fit algorithm and return a PageFitResult
    with the final (possibly adjusted) PageLayout and full debug information.

    Usage in report_builder.py:
        from app.services.page_fit import apply_page_fit
        result = apply_page_fit(proj)
        # Optionally print(result.debug_summary()) for diagnostics
        # report_builder reads result.layout via _COVER_LAYOUT dict

    Edge cases:
        - If proj has no systems, findings block is minimal → almost always fits
        - If user writes extremely long findings (>2000 chars per system),
          Stage 6 will flag overflow and identify the offending blocks
        - Font scaling in Stage 3 is rounded to 0.5 pt increments for clean rendering
    """
    layout: PageLayout = PageLayout()
    adjustments: List[str] = []

    # ── Baseline check ─────────────────────────────────────────────────────────
    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=["No adjustments needed — content fits at default spacing."],
            layout=layout, blocks=blocks,
        )

    # ── Stage 1: strip nonessential whitespace ────────────────────────────────
    layout = copy.deepcopy(layout)
    layout.bar_spacer_pt       = 0.0
    layout.body_before_pt      = 0.0
    layout.body_after_pt       = 0.0
    layout.subhead_before_pt   = 0.0
    layout.subhead_after_pt    = 0.0
    layout.table_cell_pad_pt   = 0.0
    layout.intro_after_pt      = 0.0
    layout.logo_after_pt       = 0.0
    layout.title_after_pt      = 2.0   # reduce 6 → 2 pt

    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    adjustments.append(
        f"Stage 1: stripped whitespace & spacing — {overflow_pt:.1f} pt overflow remaining"
    )
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=adjustments, layout=layout, blocks=blocks,
        )

    # ── Stage 2: zero bar cell padding ────────────────────────────────────────
    layout = copy.deepcopy(layout)
    layout.bar_before_pt = 0.0
    layout.bar_after_pt  = 0.0

    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    adjustments.append(
        f"Stage 2: zeroed bar cell padding — {overflow_pt:.1f} pt overflow remaining"
    )
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=adjustments, layout=layout, blocks=blocks,
        )

    # ── Stage 3: scale body font down (floor = body_size_min_pt) ─────────────
    layout = copy.deepcopy(layout)
    n_lines = _estimate_total_body_lines(proj, layout)
    # Each 1 pt of font reduction saves approximately n_lines × line_height_factor pt
    pts_saved_per_font_pt = max(1.0, n_lines * layout.line_height_factor)
    raw_reduction = overflow_pt / pts_saved_per_font_pt
    # Round DOWN to nearest 0.5 pt (conservative — avoids overshoot)
    font_reduction = math.floor(raw_reduction * 2) / 2.0
    font_reduction = min(font_reduction, layout.body_size_pt - layout.body_size_min_pt)
    layout.body_size_pt = max(
        layout.body_size_min_pt,
        round(layout.body_size_pt - font_reduction, 1)
    )

    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    adjustments.append(
        f"Stage 3: body font → {layout.body_size_pt:.1f} pt — {overflow_pt:.1f} pt overflow remaining"
    )
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=adjustments, layout=layout, blocks=blocks,
        )

    # ── Stage 4: scale logo down (floor = logo_width_min_in) ─────────────────
    layout = copy.deepcopy(layout)
    # Reducing logo width by X inches saves X/aspect_ratio × 72 pt of height
    # Use 1.5× overshoot factor since aspect ratio is an estimate
    logo_reduction_in = min(
        layout.logo_width_in - layout.logo_width_min_in,
        (overflow_pt / 72.0) * 1.5
    )
    layout.logo_width_in = max(
        layout.logo_width_min_in,
        round(layout.logo_width_in - logo_reduction_in, 2)
    )

    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    adjustments.append(
        f"Stage 4: logo width → {layout.logo_width_in:.2f}\" — {overflow_pt:.1f} pt overflow remaining"
    )
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=adjustments, layout=layout, blocks=blocks,
        )

    # ── Stage 5: condense cert signature row spacing ──────────────────────────
    layout = copy.deepcopy(layout)
    layout.cert_sig_before_pt = layout.cert_sig_before_min_pt
    layout.cert_sig_after_pt  = layout.cert_sig_after_min_pt

    blocks, used_pt, avail_pt, overflow_pt = _run_check(proj, layout)
    adjustments.append(
        f"Stage 5: condensed cert sig row — {overflow_pt:.1f} pt overflow remaining"
    )
    if overflow_pt <= 0:
        return PageFitResult(
            fits=True, used_pt=used_pt, available_pt=avail_pt, overflow_pt=0.0,
            adjustments=adjustments, layout=layout, blocks=blocks,
        )

    # ── Stage 6: flag overflow — do not silently break layout ─────────────────
    offending = [
        b.name for b in blocks
        if b.is_variable and b.height_pt > 80.0
    ]
    adjustments.append(
        f"Stage 6: OVERFLOW — {overflow_pt:.1f} pt ({overflow_pt/72:.3f}\") exceeds "
        f"available page height.  Consider shortening the findings/summary text."
    )
    return PageFitResult(
        fits=False,
        used_pt=used_pt,
        available_pt=avail_pt,
        overflow_pt=overflow_pt,
        adjustments=adjustments,
        offending_blocks=offending,
        layout=layout,
        blocks=blocks,
    )

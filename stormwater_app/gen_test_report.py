"""
Generate a test report for visual inspection in Word.
Run from stormwater_app directory:  py gen_test_report.py
"""
import sys, uuid, datetime
from pathlib import Path

sys.path.insert(0, ".")

from app.session import ProjectSession, ReportMeta, SystemEntry, WriteUp
from app.services.report_builder import build_report

# ── Build a realistic test project ──────────────────────────────────────────
proj = ProjectSession(
    meta=ReportMeta(
        site_name="Test Site — Geometry Validation",
        client_name="Sterling Stormwater Maintenance Services",
        site_address="123 Test Lane, Arlington, VA 22201",
        contract_number="TEST-001",
        report_type="Inspection and Maintenance",
        report_date="2026-03-20",
        inspection_date="2026-03-20",
        weather_conditions="Clear, 58°F",
        next_service_date="2026-09-20",
        prepared_by="Test Engineer",
        report_number="TEST-2026-001",
        site_description=(
            "The site is a commercial mixed-use development with three StormFilter "
            "cartridge systems and one Jellyfish Filter unit managing runoff from "
            "approximately 4.2 acres of impervious surface. Systems were last serviced "
            "in September 2025. This report documents the March 2026 inspection and "
            "maintenance performed."
        ),
    ),
    systems=[
        SystemEntry(
            entry_id="s1",
            system_type="StormFilter",
            system_id="SF-01",
            display_name="StormFilter SF-01",
            condition="Good",
            notes="Cartridges inspected and functioning normally. Minor sediment accumulation on inlet screens — cleaned in place.",
        ),
        SystemEntry(
            entry_id="s2",
            system_type="StormFilter",
            system_id="SF-02",
            display_name="StormFilter SF-02",
            condition="Fair",
            notes="Cartridge replacement due at next service interval. Inlet pipe shows minor scaling. Outlet structure clear.",
        ),
        SystemEntry(
            entry_id="s3",
            system_type="Jellyfish Filter",
            system_id="JF-01",
            display_name="Jellyfish Filter JF-01",
            condition="Good",
            notes="Filter media inspected — no replacement required. Trash rack cleared of debris. Bypass weir clear.",
        ),
    ],
    write_ups={
        "s1": WriteUp(
            findings="System operating within normal parameters. Sediment loading light.",
            recommendations="Continue monitoring on standard 6-month schedule.",
            maintenance_performed="Cleaned inlet screens, inspected cartridges, flushed sump.",
            post_service_condition="Good",
        ),
        "s2": WriteUp(
            findings="Cartridge performance has degraded; pressure differential near replacement threshold.",
            recommendations="Replace cartridges at next scheduled service (September 2026).",
            maintenance_performed="Inspected cartridges, cleaned inlet pipe scaling, checked outlet.",
            post_service_condition="Fair — schedule cartridge replacement",
        ),
        "s3": WriteUp(
            findings="System performing well. No significant debris accumulation.",
            recommendations="No corrective action required.",
            maintenance_performed="Removed trash from rack, inspected filter media, tested bypass.",
            post_service_condition="Good",
        ),
    },
    photos=[],
)

# ── Generate ─────────────────────────────────────────────────────────────────
output_path = Path("output") / "geometry_test_report.docx"
output_path.parent.mkdir(exist_ok=True)

output_filename = "geometry_test_report.docx"
result = build_report(proj, filename=output_filename, photo_grid="2x2")
print(f"build_report returned: {result!r}")
# build_report writes to OUTPUT_DIR/filename and returns the path string
output_path = Path("output") / output_filename
if output_path.exists():
    print(f"Report written to: {output_path.resolve()}")
else:
    print(f"WARNING: file not found at {output_path.resolve()}")

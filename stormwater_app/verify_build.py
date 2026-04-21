"""Quick validation that all changed modules import cleanly and key symbols exist."""
import sys
sys.path.insert(0, "C:/Users/brolf/Desktop/stormwater_report_generator/stormwater_app")

errors = []

try:
    import app.services.report_builder as rb
    assert rb._COVER_LOGO_WIDTH == 3.6,   f"cover logo {rb._COVER_LOGO_WIDTH}"
    assert rb._PHOTO_LOGO_WIDTH == 3.0,   f"photo logo {rb._PHOTO_LOGO_WIDTH}"
    assert set(rb._GRID_CFG) == {"2x2","2x3","3x3"}, f"grids {rb._GRID_CFG.keys()}"
    import inspect
    sig = inspect.getsource(rb.build_report)
    assert "photo_grid" in sig,            "photo_grid missing from build_report"
    assert hasattr(rb, "_add_black_rule"), "_add_black_rule missing"
    assert hasattr(rb, "_apply_table_style_no_outer_vborders"), "no-outer-vborders missing"
    assert hasattr(rb, "_add_cover_body_para"),    "_add_cover_body_para missing"
    assert hasattr(rb, "_add_cover_system_subheading"), "_add_cover_system_subheading missing"
    assert hasattr(rb, "_get_display_size"),       "_get_display_size missing"
    assert hasattr(rb, "_build_photo_grid_table"), "_build_photo_grid_table missing"
    assert hasattr(rb, "_add_photo_page_logo_header"), "_add_photo_page_logo_header missing"
    # footer size: check _add_footer source for size=10
    footer_src = inspect.getsource(rb._add_footer)
    assert "size=10" in footer_src, "footer size=10 missing"
    # green bar: check black text
    bar_src = inspect.getsource(rb._add_green_bar)
    assert "0x00, 0x00, 0x00" in bar_src, "green bar black text missing"
    print("[OK] report_builder")
except Exception as e:
    errors.append(f"report_builder: {e}")

try:
    from app.services.importer import extract_fields
    # Smoke-test field guard logic
    sample = (
        "Site Name & Location: Riverside Commons Number & Type of Stormwater Components Inspected:\n"
        "Inspection Performed By: J. Smith Number of Pages in Report:\n"
        "An inspection was performed on 4/18/2025. The results revealed:\n"
        "INSPECTION FINDINGS\nBioretention Cell 1\nFINDINGS HERE\nCERTIFICATION\n"
    )
    r = extract_fields(sample)
    # site_name must NOT contain "Number"
    assert "Number" not in r["site_name"], f"site_name contaminated: {r['site_name']!r}"
    # prepared_by must NOT contain "Number"
    assert "Number" not in r["prepared_by"], f"prepared_by contaminated: {r['prepared_by']!r}"
    print(f"[OK] importer  site_name={r['site_name']!r}  prepared_by={r['prepared_by']!r}  date={r['inspection_date']!r}")
except Exception as e:
    errors.append(f"importer: {e}")

try:
    # page_export — just import, don't render (Streamlit not running)
    import importlib
    spec = importlib.util.spec_from_file_location(
        "page_export",
        "C:/Users/brolf/Desktop/stormwater_report_generator/stormwater_app/app/pages/page_export.py"
    )
    src = open("C:/Users/brolf/Desktop/stormwater_report_generator/stormwater_app/app/pages/page_export.py").read()
    assert "photo_grid_choice" in src, "grid radio widget missing"
    assert "selected_grid" in src,     "selected_grid missing"
    assert "photo_grid=selected_grid" in src, "grid not passed to build_report"
    print("[OK] page_export")
except Exception as e:
    errors.append(f"page_export: {e}")

if errors:
    print("\nFAILED:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print("\nAll checks passed.")

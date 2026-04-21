"""Quick syntax check for all modified/new files."""
import ast
import sys

files = [
    "app.py",
    "app/session.py",
    "app/pages/page_landing.py",
    "app/pages/page_photosheet.py",
    "app/services/photosheet_builder.py",
    "app/components/sidebar.py",
    "app/pages/__init__.py",
]

all_ok = True
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src)
        print(f"  OK  {f}")
    except SyntaxError as e:
        print(f"  FAIL  {f}: {e}")
        all_ok = False
    except FileNotFoundError:
        print(f"  MISSING  {f}")
        all_ok = False

if all_ok:
    print("\nAll files pass syntax check.")
else:
    print("\nSome files have errors — fix before running.")
    sys.exit(1)

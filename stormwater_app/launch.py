"""
launch.py
Python-based launcher for the Stormwater Report Generator.
More reliable than batch-file piping for port cleanup and error reporting.
Run:  python launch.py
"""

import os
import sys
import subprocess
from pathlib import Path


def kill_port(port: int):
    """Kill any process currently listening on the given port."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=8
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, timeout=5
                    )
                    print(f"  Stopped existing process on port {port} (PID {pid})")
                except Exception:
                    pass
    except Exception:
        pass  # netstat unavailable — skip silently


def check_deps():
    """Return list of missing required packages."""
    required = ["streamlit", "docx", "PIL", "pdfplumber"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            # python-docx installs as 'docx' import but pip name differs
            missing.append(pkg)
    return missing


def main():
    # ── Always run from the directory containing this script ─────────────────
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)

    print()
    print("  ==========================================")
    print("   Stormwater Report Generator")
    print("  ==========================================")
    print(f"  Working dir: {script_dir}")
    print()

    # ── Verify Python version ─────────────────────────────────────────────────
    if sys.version_info < (3, 10):
        print(f"  ERROR: Python 3.10+ required (you have {sys.version})")
        print("  Download from: https://www.python.org/downloads/")
        input("\n  Press Enter to close...")
        sys.exit(1)

    # ── Check for missing packages and install if needed ──────────────────────
    missing = check_deps()
    if missing:
        print("  Installing required packages...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        if result.returncode != 0:
            print("\n  ERROR: Package install failed.")
            print("  Try running:  pip install -r requirements.txt")
            input("\n  Press Enter to close...")
            sys.exit(1)
        print("  Packages installed.\n")

    # ── Create required directories ───────────────────────────────────────────
    for d in ["output", "projects", "templates"]:
        Path(d).mkdir(exist_ok=True)

    # ── Generate Word template if missing ─────────────────────────────────────
    if not Path("templates/report_template.docx").exists():
        print("  Generating Word template...")
        subprocess.run([sys.executable, "create_template.py"])

    # ── Free port 8501 ────────────────────────────────────────────────────────
    print("  Checking port 8501...")
    kill_port(8501)

    # ── Quick import check — catch app errors BEFORE streamlit tries ──────────
    print("  Verifying app imports...")
    check = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'.');"
         "import app.session, app.constants, app.components.sidebar;"
         "from app.pages import page_setup, page_systems, page_writeups, page_export;"
         "from app.pages import page_landing, page_photosheet;"
         "from app.services import report_builder, photosheet_builder;"
         "print('OK')"],
        capture_output=True, text=True
    )
    if check.returncode != 0 or "OK" not in check.stdout:
        print()
        print("  !! IMPORT ERROR — the app will not start !!")
        print("  ─────────────────────────────────────────────")
        if check.stderr:
            print(check.stderr)
        if check.stdout and "OK" not in check.stdout:
            print(check.stdout)
        print("  ─────────────────────────────────────────────")
        input("\n  Fix the error above, then press Enter to close...")
        sys.exit(1)

    print("  Imports OK.")
    print()
    print("  Starting at http://localhost:8501")
    print("  Press Ctrl+C in this window to stop the server.")
    print()

    # ── Launch Streamlit ──────────────────────────────────────────────────────
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.headless", "false",
             "--browser.gatherUsageStats", "false"]
        )
    except KeyboardInterrupt:
        print("\n  Stopped by user (Ctrl+C).")
    except Exception as exc:
        print(f"\n  ERROR launching streamlit: {exc}")

    print()
    print("  ==========================================")
    print("   Server stopped.")
    print("   Check any error messages above.")
    print("  ==========================================")
    print()
    input("  Press Enter to close this window...")


if __name__ == "__main__":
    main()

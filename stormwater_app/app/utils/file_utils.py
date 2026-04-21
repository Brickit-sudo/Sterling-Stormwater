"""
app/utils/file_utils.py
File system helpers: safe path creation, output directory management,
and filename sanitization.
"""

import re
from pathlib import Path


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Make a string safe to use as a filename on Windows.
    Removes illegal characters, collapses spaces, truncates.
    """
    # Remove characters illegal on Windows filenames
    name = re.sub(r'[<>:"/\\|?*,]', "", name)
    # Collapse whitespace to underscores
    name = re.sub(r"\s+", "_", name.strip())
    # Remove leading/trailing dots/underscores
    name = name.strip("._")
    # Truncate
    return name[:max_length] if name else "report"


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_output_path(filename: str, output_dir: str = "output") -> Path:
    """
    Return a safe output path. If the filename already exists,
    append a counter suffix to avoid overwriting.
    """
    out_dir = ensure_dir(output_dir)
    base = Path(filename)
    stem = sanitize_filename(base.stem)
    suffix = base.suffix or ".docx"

    candidate = out_dir / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = out_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    return candidate


def list_project_files(projects_dir: str = "projects") -> list[dict]:
    """
    Scan the projects directory and return metadata for saved projects.
    Used by a future 'Open Project' dialog.
    """
    import json
    results = []
    base = Path(projects_dir)
    if not base.exists():
        return results

    for session_file in base.glob("*/session.json"):
        try:
            data = json.loads(session_file.read_text())
            results.append({
                "path": str(session_file),
                "project_id": data.get("project_id", ""),
                "site_name": data.get("meta", {}).get("site_name", "Unknown"),
                "report_type": data.get("meta", {}).get("report_type", ""),
                "report_date": data.get("meta", {}).get("report_date", ""),
                "system_count": len(data.get("systems", [])),
                "photo_count": len(data.get("photos", [])),
            })
        except Exception:
            continue

    return sorted(results, key=lambda x: x["report_date"], reverse=True)

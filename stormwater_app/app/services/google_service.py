"""
app/services/google_service.py
Google Sheets + Drive integration via service account.

Credentials stored in: stormwater_app/.google_credentials.json
Config stored in:      stormwater_app/.google_config.json
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import streamlit as st

_CREDS_PATH   = Path(__file__).parent.parent.parent / ".google_credentials.json"
_CONFIG_PATH  = Path(__file__).parent.parent.parent / ".google_config.json"

_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text())
    return {}


def save_config(cfg: dict) -> None:
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def is_configured() -> bool:
    return _CREDS_PATH.exists()


def save_credentials(creds_dict: dict) -> None:
    _CREDS_PATH.write_text(json.dumps(creds_dict, indent=2))


def load_credentials() -> Optional[dict]:
    if not _CREDS_PATH.exists():
        return None
    return json.loads(_CREDS_PATH.read_text())


# ── Auth ──────────────────────────────────────────────────────────────────────

@st.cache_resource
def _get_credentials():
    creds_dict = load_credentials()
    if not creds_dict:
        return None
    from google.oauth2.service_account import Credentials
    return Credentials.from_service_account_info(creds_dict, scopes=_DRIVE_SCOPES)


@st.cache_resource
def get_drive_service():
    creds = _get_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds)


@st.cache_resource
def get_sheets_client():
    creds_dict = load_credentials()
    if not creds_dict:
        return None
    import gspread
    return gspread.service_account_from_dict(creds_dict)


def service_email() -> str:
    c = load_credentials()
    return c.get("client_email", "") if c else ""


# ── Drive ─────────────────────────────────────────────────────────────────────

def upload_to_drive(
    file_path: str | Path,
    folder_id: str,
    file_name: str | None = None,
    make_public: bool = True,
) -> dict:
    """Upload a file to Drive. Returns {id, name, webViewLink}."""
    from googleapiclient.http import MediaFileUpload
    import mimetypes

    service = get_drive_service()
    if not service:
        raise RuntimeError("Google Drive not configured.")

    path = Path(file_path)
    name = file_name or path.name
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    meta = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(str(path), mimetype=mime, resumable=True)

    file = service.files().create(
        body=meta, media_body=media, fields="id,name,webViewLink"
    ).execute()

    if make_public:
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

    return file


def list_drive_folder(folder_id: str, name_contains: str = "") -> list[dict]:
    """List files in a Drive folder."""
    service = get_drive_service()
    if not service:
        return []
    q = f"'{folder_id}' in parents and trashed=false"
    if name_contains:
        q += f" and name contains '{name_contains}'"
    res = service.files().list(
        q=q,
        fields="files(id,name,mimeType,createdTime,webViewLink,size)",
        orderBy="createdTime desc",
        pageSize=50,
    ).execute()
    return res.get("files", [])


def create_drive_folder(name: str, parent_id: str | None = None) -> str:
    """Create a folder in Drive. Returns folder ID."""
    service = get_drive_service()
    if not service:
        raise RuntimeError("Google Drive not configured.")
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def delete_drive_file(file_id: str) -> None:
    service = get_drive_service()
    if service:
        service.files().delete(fileId=file_id).execute()


# ── Sheets ────────────────────────────────────────────────────────────────────

def sync_to_sheet(sheet_url: str, tab_name: str, rows: list[dict]) -> int:
    """Overwrite a sheet tab with rows. Returns row count."""
    gc = get_sheets_client()
    if not gc:
        raise RuntimeError("Google Sheets not configured.")
    sh = gc.open_by_url(sheet_url)
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=50)

    ws.clear()
    if not rows:
        return 0

    headers = list(rows[0].keys())
    data    = [headers] + [[str(r.get(h, "") or "") for h in headers] for r in rows]

    # Batch write in chunks of 500
    ws.update(data, "A1")
    return len(rows)


def read_from_sheet(sheet_url: str, tab_name: str = "Sheet1") -> list[dict]:
    """Read all records from a sheet tab."""
    gc = get_sheets_client()
    if not gc:
        return []
    sh = gc.open_by_url(sheet_url)
    ws = sh.worksheet(tab_name)
    return ws.get_all_records()


def append_row_to_sheet(sheet_url: str, tab_name: str, row: dict) -> None:
    """Append a single row to a sheet tab."""
    gc = get_sheets_client()
    if not gc:
        raise RuntimeError("Google Sheets not configured.")
    sh = gc.open_by_url(sheet_url)
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=50)
    ws.append_row(list(row.values()))


def test_connection() -> tuple[bool, str]:
    """Test Drive + Sheets connectivity. Returns (ok, message)."""
    try:
        svc = get_drive_service()
        if not svc:
            return False, "No credentials loaded."
        about = svc.about().get(fields="user").execute()
        email = about.get("user", {}).get("emailAddress", "unknown")
        return True, f"Connected as {email}"
    except Exception as e:
        return False, str(e)

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

_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
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
    return Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)


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


@st.cache_resource
def get_gmail_service(user_email: str = ""):
    """Gmail API service. Requires domain-wide delegation for non-service-account sends."""
    try:
        from googleapiclient.discovery import build
        creds = _get_credentials()
        if not creds:
            return None
        if user_email:
            creds = creds.with_subject(user_email)
        return build("gmail", "v1", credentials=creds)
    except Exception:
        return None


@st.cache_resource
def get_calendar_service(user_email: str = ""):
    """Google Calendar API service."""
    try:
        from googleapiclient.discovery import build
        creds = _get_credentials()
        if not creds:
            return None
        if user_email:
            creds = creds.with_subject(user_email)
        return build("calendar", "v3", credentials=creds)
    except Exception:
        return None


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


def send_email(to: str, subject: str, html_body: str,
               sender: str = "", attachments: list = []) -> bool:
    """Send email via Gmail API. sender must be the impersonated user's email."""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    try:
        svc = get_gmail_service(sender)
        if not svc:
            return False
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["From"] = sender
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception:
        return False


def create_calendar_event(calendar_id: str, summary: str, start_date: str,
                           end_date: str = "", description: str = "",
                           attendees: list[str] = [], user_email: str = "") -> str | None:
    """Create a Google Calendar event. Returns event ID or None on failure.
    start_date / end_date are ISO date strings (YYYY-MM-DD) for all-day events."""
    try:
        svc = get_calendar_service(user_email)
        if not svc:
            return None
        end = end_date or start_date
        event = {
            "summary": summary,
            "description": description,
            "start": {"date": start_date},
            "end":   {"date": end},
            "attendees": [{"email": e} for e in attendees if e],
        }
        result = svc.events().insert(calendarId=calendar_id, body=event).execute()
        return result.get("id")
    except Exception:
        return None


def export_to_notebooklm(content: str, filename: str, folder_id: str = "") -> str | None:
    """Upload a plain-text document to Google Drive for NotebookLM ingestion.
    Returns the Drive file URL or None on failure."""
    try:
        from googleapiclient.http import MediaInMemoryUpload
        svc = get_drive_service()
        if not svc:
            return None
        cfg = load_config()
        fid = folder_id or cfg.get("notebooklm_folder_id", "")
        meta = {"name": filename, "mimeType": "application/vnd.google-apps.document"}
        if fid:
            meta["parents"] = [fid]
        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain")
        f = svc.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
        return f.get("webViewLink")
    except Exception:
        return None


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


def list_site_subfolders(root_folder_id: str) -> list[dict]:
    """Returns [{id, name}] for each subfolder inside root_folder_id."""
    service = get_drive_service()
    if not service:
        return []
    q = f"'{root_folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
    res = service.files().list(q=q, fields="files(id,name)", pageSize=200).execute()
    return res.get("files", [])


def _list_files_recursive(folder_id: str, service) -> list[dict]:
    """Recursively list all non-folder files under folder_id, including nested subfolders."""
    results = []
    # Get files directly in this folder
    q_files = f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'"
    token = None
    while True:
        kwargs = dict(q=q_files, fields="nextPageToken,files(id,name,mimeType,createdTime,modifiedTime,size,webViewLink)", pageSize=200)
        if token:
            kwargs["pageToken"] = token
        res = service.files().list(**kwargs).execute()
        results.extend(res.get("files", []))
        token = res.get("nextPageToken")
        if not token:
            break
    # Recurse into subfolders
    q_folders = f"'{folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
    sub_res = service.files().list(q=q_folders, fields="files(id,name)", pageSize=200).execute()
    for sub in sub_res.get("files", []):
        results.extend(_list_files_recursive(sub["id"], service))
    return results


def list_site_files(site_folder_id: str) -> list[dict]:
    """Returns all non-folder files in a site folder and all its subfolders."""
    service = get_drive_service()
    if not service:
        return []
    return _list_files_recursive(site_folder_id, service)


def _guess_type(name: str, ext: str) -> str:
    n = name.lower()
    if "invoice" in n:
        return "invoice"
    if "proposal" in n:
        return "proposal"
    if "maintenance" in n:
        return "maintenance_report"
    if "inspection" in n or "compliance" in n:
        return "inspection_report"
    if ext in ("jpg", "jpeg", "png"):
        return "photo"
    return "other"


def crawl_drive_folder(root_folder_id: str) -> list[dict]:
    """Walk root → site subfolders → all files (recursive). Returns flat list of file metadata dicts."""
    records = []
    for site in list_site_subfolders(root_folder_id):
        for f in list_site_files(site["id"]):
            name = f.get("name", "")
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            records.append({
                "site_name":       site["name"],
                "site_folder_id":  site["id"],
                "file_id":         f["id"],
                "file_name":       name,
                "file_ext":        ext,
                "guessed_type":    _guess_type(name, ext),
                "mime":            f.get("mimeType", ""),
                "created":         f.get("createdTime", ""),
                "modified":        f.get("modifiedTime", ""),
                "size_bytes":      f.get("size", ""),
                "url":             f.get("webViewLink", ""),
            })
    return records


def download_pdf_text(file_id: str) -> str:
    """Download a PDF from Drive and extract its text with pdfplumber. Returns raw text string."""
    import io
    import pdfplumber
    from googleapiclient.http import MediaIoBaseDownload

    service = get_drive_service()
    if not service:
        return ""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    pages = []
    with pdfplumber.open(buf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)

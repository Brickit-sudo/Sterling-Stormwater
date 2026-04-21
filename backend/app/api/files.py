import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db
from app.models.client import Client
from app.models.site import Site
from app.models.file_record import FileRecord
from app.models.user import User, UserRole
from app.models.user_site_assignment import UserSiteAssignment
from app.schemas.file_record import FileRecordOut, UploadResponse, ReportAnalysis, SystemAnalysis
from app.services.analyzer import analyze_report
from app.dependencies import get_current_user

router = APIRouter(prefix="/files", tags=["files"])


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s_-]+", "_", text)[:40] or "unknown"


async def _find_or_create_client(db: AsyncSession, name: str) -> Client:
    result = await db.execute(select(Client).where(Client.name == name))
    client = result.scalar_one_or_none()
    if not client:
        client = Client(name=name)
        db.add(client)
        await db.flush()
    return client


async def _find_or_create_site(db: AsyncSession, client_id: uuid.UUID, name: str, address: str | None) -> Site:
    result = await db.execute(select(Site).where(Site.client_id == client_id, Site.name == name))
    site = result.scalar_one_or_none()
    if not site:
        site = Site(client_id=client_id, name=name, address=address)
        db.add(site)
        await db.flush()
    elif address and not site.address:
        site.address = address
    return site


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    client_name: str | None = Form(default=None),
    site_name:   str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()
    file_hash  = hashlib.sha256(file_bytes).hexdigest()
    file_type  = Path(file.filename).suffix.lower().lstrip(".")

    # ── Run full analysis ─────────────────────────────────────────────────────
    analysis_raw = analyze_report(file.filename, file_bytes)

    def _make_analysis(a: dict) -> ReportAnalysis:
        return ReportAnalysis(
            site_info=a["site_info"],
            systems=[SystemAnalysis(**s) for s in a["systems"]],
            photo_captions=a["photo_captions"],
            recommendations=a["recommendations"],
            introduction=a["introduction"],
            sections=a["sections"],
            error=a.get("error"),
        )

    # ── Deduplication check ───────────────────────────────────────────────────
    existing = await db.execute(select(FileRecord).where(FileRecord.file_hash == file_hash))
    existing_record = existing.scalar_one_or_none()
    if existing_record:
        return UploadResponse(
            file=FileRecordOut.model_validate(existing_record),
            analysis=_make_analysis(analysis_raw),
            is_duplicate=True,
        )

    # Use extracted names if not provided
    if not client_name:
        raise HTTPException(status_code=422, detail="client_name is required")
    fields          = analysis_raw["site_info"]
    resolved_client = client_name
    resolved_site   = site_name   or fields.get("site_name", "") or file.filename

    # ── Resolve site in DB ────────────────────────────────────────────────────
    client = await _find_or_create_client(db, resolved_client)
    site   = await _find_or_create_site(db, client.client_id, resolved_site, fields.get("site_address"))

    # ── Save file to archive ──────────────────────────────────────────────────
    client_slug = _slugify(resolved_client)
    site_slug   = _slugify(resolved_site)
    date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    dest_dir    = Path(settings.file_storage_path) / client_slug / site_slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path   = dest_dir / f"{date_prefix}__{file_hash[:8]}.{file_type}"
    dest_path.write_bytes(file_bytes)

    # ── Create FileRecord ─────────────────────────────────────────────────────
    record = FileRecord(
        site_id=site.site_id,
        original_name=file.filename,
        stored_path=str(dest_path.resolve()),
        file_hash=file_hash,
        file_type=file_type,
        uploaded_by=current_user.user_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return UploadResponse(
        file=FileRecordOut.model_validate(record),
        analysis=_make_analysis(analysis_raw),
        is_duplicate=False,
    )


def _is_scoped(role: UserRole) -> bool:
    return role in (UserRole.inspector, UserRole.technician, UserRole.client_portal)


@router.get("/", response_model=list[FileRecordOut])
async def list_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FileRecord).order_by(FileRecord.imported_at.desc())
    if _is_scoped(current_user.role):
        stmt = stmt.join(Site, FileRecord.site_id == Site.site_id).join(
            UserSiteAssignment,
            (UserSiteAssignment.site_id == Site.site_id)
            & (UserSiteAssignment.user_id == current_user.user_id),
        )
    result = await db.execute(stmt)
    return [FileRecordOut.model_validate(r) for r in result.scalars().all()]


async def _assert_file_access(db: AsyncSession, user: User, record: FileRecord) -> None:
    if not _is_scoped(user.role):
        return
    result = await db.execute(
        select(UserSiteAssignment).where(
            UserSiteAssignment.site_id == record.site_id,
            UserSiteAssignment.user_id == user.user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Access to this file is not authorized")


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FileRecord).where(FileRecord.file_id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    await _assert_file_access(db, current_user, record)
    path = Path(record.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(
        path=str(path),
        filename=record.original_name,
        media_type="application/octet-stream",
    )


@router.post("/{file_id}/reprocess", response_model=UploadResponse)
async def reprocess_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(FileRecord).where(FileRecord.file_id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    await _assert_file_access(db, current_user, record)
    path = Path(record.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    file_bytes   = path.read_bytes()
    analysis_raw = analyze_report(record.original_name, file_bytes)

    def _make_analysis(a: dict) -> ReportAnalysis:
        return ReportAnalysis(
            site_info=a["site_info"],
            systems=[SystemAnalysis(**s) for s in a["systems"]],
            photo_captions=a["photo_captions"],
            recommendations=a["recommendations"],
            introduction=a["introduction"],
            sections=a["sections"],
            error=a.get("error"),
        )

    return UploadResponse(
        file=FileRecordOut.model_validate(record),
        analysis=_make_analysis(analysis_raw),
        is_duplicate=False,
    )

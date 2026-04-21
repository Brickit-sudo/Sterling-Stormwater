"""
app/services/photo_service.py
Photo file management: copying uploads to project folder, EXIF reading,
thumbnail generation, HEIC conversion.
"""

import io
import shutil
from pathlib import Path
from typing import Optional

# ── Optional HEIC/HEIF support via pillow-heif ───────────────────────────────
# Install with:  pip install pillow-heif
try:
    from pillow_heif import register_heif_opener as _register_heif
    _register_heif()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

PROJECTS_DIR = Path("projects")

# File extensions accepted for upload.
# HEIC/HEIF are always listed so users can attempt to upload iPhone photos.
# If pillow-heif is not installed, save_uploaded_photo() raises a clear
# ValueError with installation instructions instead of silently failing.
UPLOAD_TYPES = ["jpg", "jpeg", "png", "heic", "heif"]


def _apply_exif_orientation(img):
    """Apply EXIF orientation tag so portrait photos display upright."""
    try:
        from PIL import ImageOps
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def _to_jpeg_bytes(img, quality: int = 90) -> bytes:
    """Convert a PIL Image to JPEG bytes, handling alpha channels."""
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def correct_orientation_bytes(raw_bytes: bytes) -> bytes:
    """
    Return orientation-corrected JPEG bytes from any supported image format.
    Used for previews — preserves full resolution so quality stays sharp.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        img = _apply_exif_orientation(img)
        return _to_jpeg_bytes(img, quality=92)
    except Exception:
        return raw_bytes


def save_uploaded_photo(uploaded_file, project_id: str) -> str:
    """
    Save an uploaded photo to the project's photos folder.
    HEIC/HEIF files are automatically converted to JPEG.
    EXIF orientation is applied so photos are stored right-side-up.
    Returns the absolute path string.
    """
    photo_dir = PROJECTS_DIR / project_id / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)

    name = uploaded_file.name
    is_heic = Path(name).suffix.lower() in (".heic", ".heif")

    if is_heic:
        # Require pillow-heif for HEIC conversion.
        # Raise a descriptive ValueError so the UI can surface it to the user
        # rather than silently failing or saving a broken file.
        if not HEIC_SUPPORTED:
            raise ValueError(
                "HEIC/HEIF file detected but the `pillow-heif` library is not installed.\n"
                "Fix: run  pip install pillow-heif  then restart the app."
            )
        try:
            from PIL import Image
            uploaded_file.seek(0)
            img = Image.open(io.BytesIO(uploaded_file.read()))
            img = _apply_exif_orientation(img)
            name = Path(name).stem + ".jpg"
            dest = photo_dir / name
            stem, suffix = dest.stem, dest.suffix
            counter = 1
            while dest.exists():
                dest = photo_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            dest.write_bytes(_to_jpeg_bytes(img, quality=90))
            return str(dest.resolve())
        except ValueError:
            raise   # re-raise our descriptive error unchanged
        except Exception as exc:
            raise RuntimeError(f"HEIC conversion failed for {name}: {exc}") from exc

    dest = photo_dir / name
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = photo_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    uploaded_file.seek(0)
    dest.write_bytes(uploaded_file.read())
    return str(dest.resolve())


def get_photo_bytes(filepath: str) -> Optional[bytes]:
    """Read photo bytes from disk, or None if missing."""
    p = Path(filepath)
    if p.exists():
        return p.read_bytes()
    return None


def read_exif_date(filepath: str) -> Optional[str]:
    """
    Attempt to read the capture date from EXIF metadata.
    Returns date string like 'March 14, 2026' or None.
    V1: Basic PIL EXIF read. V2: Use piexif for full tag support.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(filepath)
        exif_data = img._getexif()  # type: ignore
        if not exif_data:
            return None

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                # Format: "2026:03:14 14:23:00"
                from datetime import datetime
                dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                return dt.strftime("%B %d, %Y")
    except Exception:
        pass
    return None


def generate_thumbnail(filepath: str, max_size: tuple = (600, 600)) -> Optional[bytes]:
    """
    Return JPEG thumbnail bytes for display.
    Applies EXIF orientation so portrait photos display upright.
    Default max_size is 600×600 to preserve preview quality.
    """
    try:
        from PIL import Image
        img = Image.open(filepath)
        img = _apply_exif_orientation(img)   # fix orientation before thumbnailing
        img.thumbnail(max_size, Image.LANCZOS)
        return _to_jpeg_bytes(img, quality=88)
    except Exception:
        return None


def resize_for_report(filepath: str, max_width_px: int = 1800) -> bytes:
    """
    Resize a photo for embedding in the DOCX (avoids enormous file sizes).
    Returns JPEG bytes.
    """
    from PIL import Image
    img = Image.open(filepath)

    # Auto-orient based on EXIF
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Resize if too large
    if img.width > max_width_px:
        ratio = max_width_px / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width_px, new_height), Image.LANCZOS)

    # Convert RGBA → RGB (DOCX doesn't support alpha channel PNGs well)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()

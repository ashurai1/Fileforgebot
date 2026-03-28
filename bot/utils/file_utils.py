"""
ConvertX Bot - File Utility Functions
Handles MIME detection, file validation, temporary file management, and cleanup.
"""

import mimetypes
import os
import uuid
from pathlib import Path

from bot.config import MAX_FILE_SIZE, TEMP_DIR, SUPPORTED_MIME_TYPES, logger


def get_temp_path(extension: str) -> Path:
    """Generate a unique temporary file path with the given extension."""
    if not extension.startswith("."):
        extension = f".{extension}"
    filename = f"{uuid.uuid4().hex}{extension}"
    return TEMP_DIR / filename


def detect_mime(file_path: str | Path) -> str:
    """Detect MIME type of a file using mimetypes with fallback."""
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


def validate_file_size(file_size: int | None) -> tuple[bool, str]:
    """
    Validate that the file size is within limits.
    Returns (is_valid, error_message).
    """
    if file_size is None:
        return False, "❌ Could not determine file size."
    if file_size > MAX_FILE_SIZE:
        size_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"❌ File too large! Maximum allowed size is {size_mb:.0f} MB."
    return True, ""


def validate_file_type(
    mime_type: str | None, allowed_category: str
) -> tuple[bool, str]:
    """
    Validate that the MIME type is in the allowed category.
    Categories: 'pdf', 'docx', 'image'.
    Returns (is_valid, error_message).
    """
    if mime_type is None:
        return False, "❌ Could not detect file type."
    allowed = SUPPORTED_MIME_TYPES.get(allowed_category, [])
    if mime_type not in allowed:
        expected = ", ".join(allowed)
        return False, f"❌ Unsupported file type.\nExpected: {expected}\nGot: {mime_type}"
    return True, ""


def auto_rename(original_name: str, conversion_type: str) -> str:
    """
    Generate an automatic output filename based on the original name
    and the conversion type.

    Examples:
        auto_rename("report.pdf", "pdf_to_docx") -> "report_converted.docx"
        auto_rename("photo.jpg", "img_to_pdf")   -> "photo_converted.pdf"
    """
    stem = Path(original_name).stem if original_name else "output"

    extension_map = {
        "pdf_to_docx": ".docx",
        "docx_to_pdf": ".pdf",
        "img_to_pdf": ".pdf",
        "merge_images": ".pdf",
        "split_pdf": ".pdf",
        "compress_pdf": ".pdf",
        "extract_images": ".zip",
        "pdf_to_images": ".zip",
    }
    ext = extension_map.get(conversion_type, ".bin")
    return f"{stem}_converted{ext}"


def cleanup_files(*paths: str | Path) -> None:
    """Safely remove temporary files, logging any errors."""
    for p in paths:
        try:
            path = Path(p)
            if path.exists():
                path.unlink()
                logger.debug("Cleaned up temporary file: %s", path)
        except OSError as exc:
            logger.warning("Failed to clean up %s: %s", p, exc)


def cleanup_temp_dir() -> None:
    """Remove all files in the temp directory (used on shutdown)."""
    try:
        for item in TEMP_DIR.iterdir():
            if item.is_file():
                item.unlink()
        logger.info("Cleaned up temp directory: %s", TEMP_DIR)
    except OSError as exc:
        logger.warning("Failed to clean temp directory: %s", exc)

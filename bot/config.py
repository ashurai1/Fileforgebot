"""
ConvertX Bot - Configuration Module
Loads environment variables, defines constants, and configures logging.
"""

import os
import logging
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set. Check your .env file.")

# ---------------------------------------------------------------------------
# File handling constants
# ---------------------------------------------------------------------------
MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB (Telegram bot API limit)
TEMP_DIR: Path = Path(tempfile.gettempdir()) / "convertx_bot"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX_OPS: int = int(os.getenv("RATE_LIMIT_MAX_OPS", "10"))
RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# ---------------------------------------------------------------------------
# Queue / workers
# ---------------------------------------------------------------------------
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "3"))

# ---------------------------------------------------------------------------
# Supported MIME types (used for strict validation)
# ---------------------------------------------------------------------------
SUPPORTED_MIME_TYPES: dict[str, list[str]] = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
    "image": [
        "image/jpeg",
        "image/png",
        "image/webp",
    ],
}

# Quick flat set for fast lookup
ALL_SUPPORTED_MIMES: set[str] = {
    mime for mimes in SUPPORTED_MIME_TYPES.values() for mime in mimes
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR: Path = Path(os.getenv("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("convertx")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler (5 MB × 3 backups)
    fh = RotatingFileHandler(
        LOG_DIR / "convertx.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_logging()

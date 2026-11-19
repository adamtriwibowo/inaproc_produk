"""Konfigurasi aplikasi (semua bisa ditimpa lewat variabel lingkungan)."""
import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Folder kit (data/, templates/, knowledge/). Default: dua tingkat di atas backend (root proyek).
KIT_DIR = Path(os.environ.get("INAPROC_KIT_DIR", BACKEND_DIR.parent.parent)).resolve()
DATA_DIR = KIT_DIR / "data"
TEMPLATES_SRC = KIT_DIR / "templates"
GOLDEN_DIR = DATA_DIR / "contoh_berhasil_diunggah"

STORAGE_DIR = Path(os.environ.get("INAPROC_STORAGE_DIR", BACKEND_DIR / "storage")).resolve()
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(STORAGE_DIR / 'app.db').as_posix()}")

_secret_file = STORAGE_DIR / ".secret_key"
if os.environ.get("INAPROC_SECRET_KEY"):
    SECRET_KEY = os.environ["INAPROC_SECRET_KEY"]
else:
    if not _secret_file.exists():
        _secret_file.write_text(secrets.token_urlsafe(48))
    SECRET_KEY = _secret_file.read_text().strip()

TOKEN_HOURS = int(os.environ.get("INAPROC_TOKEN_HOURS", "12"))
COOKIE_SECURE = os.environ.get("INAPROC_COOKIE_SECURE", "0") == "1"
ADMIN_EMAIL = os.environ.get("INAPROC_ADMIN_EMAIL", "admin@example.local")
ADMIN_PASSWORD = os.environ.get("INAPROC_ADMIN_PASSWORD")  # kosong -> dibuat acak & dicetak sekali
SEED_ON_START = os.environ.get("INAPROC_SEED", "1") == "1"
MAX_ZIP_BYTES = 50 * 1024 * 1024

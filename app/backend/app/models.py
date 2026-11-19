"""Model data. Semua tabel milik perusahaan memiliki company_id."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


def now():
    return datetime.now(timezone.utc)


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    store_name: str = ""
    inaproc_email: str = ""          # teks saja, TANPA password
    institution_id: str = Field(index=True, unique=True)
    scale: str = ""
    logo: str = ""
    active: bool = True
    created_at: datetime = Field(default_factory=now)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str = ""
    password_hash: str
    is_super: bool = False
    active: bool = True
    created_at: datetime = Field(default_factory=now)


class Membership(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "company_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    company_id: int = Field(index=True)
    role: str  # admin | operator | reviewer


# ---- data global (cache bersama) ----
class KbliName(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("code", "version"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    version: str
    name: str = ""


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    l1: str = Field(index=True)
    l2: str = Field(index=True)
    l3: str = Field(index=True)
    product_type: str = "B"           # B | J | DIGITAL
    uuid: Optional[str] = Field(default=None, index=True)   # diisi belakangan
    kbli_codes: list = Field(default_factory=list, sa_column=Column(JSON))  # ["46691|2020", ...]


# ---- data per perusahaan ----
class CompanyKbli(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("company_id", "code", "version"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    code: str
    version: str
    name: str = ""


class CompanyProductCount(SQLModel, table=True):
    """Produk yang sudah ada di INAPROC per kategori (nama L3)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    l3: str
    count: int = 0


class TemplateSchema(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    slug: str
    category_name: str = ""
    filename: str
    stored_path: str
    institution_id: str = ""
    category_uuid: str = ""
    template_id: str = ""
    jenis: str = "Barang"             # Barang | Jasa
    category_id: Optional[int] = Field(default=None, index=True)  # Category.id (jika cocok)
    category_path: str = ""
    columns: list = Field(default_factory=list, sa_column=Column(JSON))
    kbki: list = Field(default_factory=list, sa_column=Column(JSON))
    negara: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


class Batch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    name: str
    status: str = "Draft"
    is_test: bool = False
    pdn_preset: str = "Lokal"          # Lokal | Impor
    created_by: int
    reviewed_by: Optional[int] = None
    review_note: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class ProductRow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: int = Field(index=True)
    schema_id: Optional[int] = None
    position: int = 0
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))   # kunci = huruf kolom template
    kbki_guess: bool = False
    upload_status: str = ""            # "" | berhasil | gagal
    upload_message: str = ""
    # --- Fase 2 (AI) ---
    origin: str = "Manual"             # Manual | Draf AI
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    confirmed_ack: list = Field(default_factory=list, sa_column=Column(JSON))   # kolom kritis yang dikonfirmasi
    ai_original: dict = Field(default_factory=dict, sa_column=Column(JSON))     # nilai asli AI (audit akurasi)
    ai_meta: dict = Field(default_factory=dict, sa_column=Column(JSON))         # skor kategori, alternatif, dll.


class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: int = Field(index=True)
    row_id: Optional[int] = None
    filename: str                      # nama asli (untuk pencocokan)
    path: str                          # file PNG hasil proses
    public_url: str = ""
    width: int = 0
    height: int = 0
    size: int = 0
    kind: str = "foto"                 # foto | banner


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, index=True)
    user_id: Optional[int] = None
    user_email: str = ""
    action: str
    detail: str = ""
    ts: datetime = Field(default_factory=now)


class UploadHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: int = Field(index=True)
    file_name: str = ""
    result: str = "berhasil"           # berhasil | gagal
    message: str = ""
    user_id: Optional[int] = None
    ts: datetime = Field(default_factory=now)


# ================= Fase 2: AI =================
class AiSettings(SQLModel, table=True):
    """company_id kosong = pengaturan global organisasi (Super Admin)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, index=True)
    api_key_enc: str = ""                                   # terenkripsi (Fernet); tidak pernah dikirim ke frontend
    slots: dict = Field(default_factory=dict, sa_column=Column(JSON))   # {"model_ekstraksi": {"model":..,"fallback":..}, ...}
    quota_usd: Optional[float] = None                       # kuota bulanan
    name_pattern: str = "[Jenis] [Merek] [Tipe] [Spesifikasi kunci]"
    no_data_retention: bool = False                         # provider routing: data_collection=deny
    image_generate_enabled: bool = False                    # tahap 4
    updated_at: datetime = Field(default_factory=now)


class AiUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    user_id: Optional[int] = None
    batch_id: Optional[int] = None
    job_id: Optional[int] = None
    slot: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    status: str = "ok"                 # ok | error | gagal_validasi
    note: str = ""
    ts: datetime = Field(default_factory=now, index=True)


class AiJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: Optional[int] = None
    user_id: Optional[int] = None
    kind: str = "impor"
    status: str = "antri"              # antri | berjalan | selesai | gagal | dibatalkan
    progress: int = 0                  # 0-100
    message: str = ""
    params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
    finished_at: Optional[datetime] = None


class SourceDoc(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: Optional[int] = None
    filename: str
    kind: str = "xlsx"                 # xlsx | csv | pdf | image
    path: str
    size: int = 0
    sha256: str = ""
    uploaded_by: Optional[int] = None
    created_at: datetime = Field(default_factory=now)


class CellSource(SQLModel, table=True):
    """Sumber setiap isian yang diisi AI: file, lokasi, dan potongan teks asli."""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    row_id: int = Field(index=True)
    col: str
    doc_id: Optional[int] = None
    doc_name: str = ""
    location: str = ""                 # mis. "baris 12", "halaman 3"
    quote: str = ""
    verified: bool = True              # False = tidak bisa diverifikasi otomatis (mis. PDF)


class PricingRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    scope: str = "semua"               # semua | l1 | l2 | l3
    category_name: str = ""            # nama L1/L2/L3 sesuai scope
    markup_pct: float = 0.0
    rounding: int = 0                  # bulatkan ke kelipatan ini (0 = tanpa pembulatan)
    min_price: int = 0


class AiFinding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True)
    batch_id: int = Field(index=True)
    row_id: Optional[int] = None
    col: str = ""
    kind: str = ""
    message: str = ""
    severity: str = "warn"             # warn | info
    ts: datetime = Field(default_factory=now)

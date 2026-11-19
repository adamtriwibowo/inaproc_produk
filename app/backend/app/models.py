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

"""Seed awal dari dataset di folder data/ (tanpa scraping ulang)."""
import json
import re
import secrets
import shutil

from sqlmodel import Session, select

from .. import config
from ..models import Category, Company, CompanyKbli, CompanyProductCount, KbliName, Membership, TemplateSchema, User
from ..security import hash_password
from . import kelayakan
from .template_scan import scan_workbook

PT_KIG = {
    "name": "Katalog Indonesia Group", "store_name": "pt.kig",
    "inaproc_email": "ptkatalogindonesiagroup@gmail.com",
    "institution_id": "01J8T3EVSG6715EVP9CF9ZQV4V",
}


def seed_global(s: Session):
    """Pohon kategori + nama KBLI (global)."""
    if s.exec(select(Category).limit(1)).first():
        return
    d = json.loads((config.DATA_DIR / "inaproc_kategori_kbli.json").read_text(encoding="utf-8"))
    l1, l2, cd = d["l1"], d["l2"], d["cd"]
    for i1, i2, name, ptype, codes, _ok in d["rows"]:
        s.add(Category(l1=l1[i1], l2=l2[i2].split("»", 1)[1], l3=name, product_type=ptype,
                       kbli_codes=[cd[c].replace("/", "|") for c in codes]))
    nk = json.loads((config.DATA_DIR / "inaproc_nama_kbli.json").read_text(encoding="utf-8"))
    for key, ver in (("k20", "2020"), ("k25", "2025")):
        for code, nm in nk.get(key, {}).items():
            s.add(KbliName(code=code, version=ver, name=nm))
    s.commit()
    kelayakan.invalidate()


def import_template_bytes(s: Session, company: Company, data: bytes, filename: str) -> TemplateSchema:
    """Simpan template sebagai skema perusahaan. Melempar ValueError bila ditolak."""
    from .template_scan import TemplateError
    sc = scan_workbook(data, filename)
    if sc["institution_id"] != company.institution_id:
        raise TemplateError(
            f"Template ini milik perusahaan lain (Institution ID {sc['institution_id']}, "
            f"perusahaan aktif {company.institution_id}).")
    cat = s.exec(select(Category).where(Category.uuid == sc["category_uuid"])).first()
    if not cat:
        # pencocokan sementara lewat nama L3 (+ jenis)
        want = "J" if sc["jenis"] == "Jasa" else "B"
        cands = [c for c in kelayakan.all_categories(s) if c.l3.lower() == sc["category_name"].lower() and c.product_type == want]
        if len(cands) >= 1:
            cat = cands[0]
            cat.uuid = sc["category_uuid"]
            s.add(cat)
            kelayakan.invalidate()
    if cat:
        kset = kelayakan.kbli_set(s, company.id)
        if not kelayakan.is_ok(cat, kset):
            raise TemplateError(f"Kategori '{cat.l3}' berstatus Tidak Bisa untuk KBLI perusahaan ini — template ditolak.")
    dest_dir = config.STORAGE_DIR / f"company_{company.id}" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(data)
    old = s.exec(select(TemplateSchema).where(TemplateSchema.company_id == company.id, TemplateSchema.slug == sc["slug"])).first()
    obj = old or TemplateSchema(company_id=company.id, slug=sc["slug"], filename=filename, stored_path=str(dest))
    for k in ("category_name", "institution_id", "category_uuid", "template_id", "jenis", "columns", "kbki", "negara"):
        setattr(obj, k, sc[k])
    if old and old.filename != filename:
        try:
            (dest_dir / old.filename).unlink(missing_ok=True)
        except OSError:
            pass
    obj.filename, obj.stored_path = filename, str(dest)
    obj.category_id = cat.id if cat else None
    obj.category_path = f"{cat.l1} › {cat.l2} › {cat.l3}" if cat else ""
    s.add(obj)
    s.commit()
    s.refresh(obj)
    return obj


def seed_company_kig(s: Session):
    c = s.exec(select(Company).where(Company.institution_id == PT_KIG["institution_id"])).first()
    if c:
        return c
    c = Company(**PT_KIG, scale="")
    s.add(c)
    s.commit()
    s.refresh(c)
    kb = json.loads((config.DATA_DIR / "kbli_perusahaan.json").read_text(encoding="utf-8"))
    for k in kb:
        s.add(CompanyKbli(company_id=c.id, code=str(k["kode"]), version=str(k["versi"]), name=k.get("nama", "")))
    ex = json.loads((config.DATA_DIR / "produk_existing_pt_kig.json").read_text(encoding="utf-8"))
    for name, n in ex.items():
        s.add(CompanyProductCount(company_id=c.id, l3=name, count=n))
    s.commit()
    if config.TEMPLATES_SRC.exists():
        for f in sorted(config.TEMPLATES_SRC.glob("*Unggah_Produk_Sekaligus*.xlsx")):
            try:
                import_template_bytes(s, c, f.read_bytes(), f.name)
            except ValueError as e:  # noqa: PERF203
                print(f"[seed] template dilewati {f.name}: {e}")
    return c


def seed_admin(s: Session):
    if s.exec(select(User).where(User.is_super == True)).first():  # noqa: E712
        return
    pw = config.ADMIN_PASSWORD or secrets.token_urlsafe(12)
    s.add(User(email=config.ADMIN_EMAIL.lower(), name="Super Admin", password_hash=hash_password(pw), is_super=True))
    s.commit()
    if not config.ADMIN_PASSWORD:
        print("=" * 60)
        print(f"[seed] Super Admin dibuat: {config.ADMIN_EMAIL}  password: {pw}")
        print("[seed] Simpan password ini sekarang; tidak akan ditampilkan lagi.")
        print("=" * 60)


def run_seed(s: Session):
    seed_global(s)
    seed_company_kig(s)
    seed_admin(s)

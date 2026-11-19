"""Perusahaan aktif: profil, anggota, KBLI, dashboard, audit log."""
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import func, select

from ..deps import ROLES, ROLE_LABEL, Ctx, any_member, audit, need
from ..models import AuditLog, Batch, CompanyKbli, KbliName, Membership, ProductRow, User
from ..services import kelayakan

router = APIRouter(prefix="/api/companies/{company_id}", tags=["perusahaan"])


class KbliIn(BaseModel):
    code: str
    version: str = "2020"
    name: str = ""


class MemberIn(BaseModel):
    email: str
    role: str


def company_dict(c):
    return {"id": c.id, "name": c.name, "store_name": c.store_name, "inaproc_email": c.inaproc_email,
            "institution_id": c.institution_id, "scale": c.scale, "logo": c.logo}


@router.get("")
def get_company(ctx: Ctx = Depends(any_member)):
    return {**company_dict(ctx.company), "role": ctx.role, "role_label": ROLE_LABEL.get(ctx.role, "Super Admin")}


@router.patch("")
def patch_company(body: dict, ctx: Ctx = Depends(need("admin"))):
    c = ctx.company
    for k in ("store_name", "inaproc_email", "scale", "logo"):
        if k in body:
            setattr(c, k, body[k])
    ctx.session.add(c)
    ctx.session.commit()
    audit(ctx.session, ctx.user, c.id, "perusahaan.profil", ",".join(body.keys()))
    return company_dict(c)


# ---- anggota ----
@router.get("/members")
def members(ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    out = []
    for m in s.exec(select(Membership).where(Membership.company_id == ctx.company.id)):
        u = s.get(User, m.user_id)
        out.append({"user_id": u.id, "email": u.email, "name": u.name, "role": m.role})
    return out


@router.put("/members")
def set_member(body: MemberIn, ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    if body.role not in ROLES:
        raise HTTPException(400, "Role tidak valid")
    u = s.exec(select(User).where(User.email == body.email.strip().lower())).first()
    if not u:
        raise HTTPException(404, "Pengguna belum terdaftar — minta Super Admin mengundangnya terlebih dahulu")
    m = s.exec(select(Membership).where(Membership.user_id == u.id, Membership.company_id == ctx.company.id)).first()
    if m:
        m.role = body.role
    else:
        m = Membership(user_id=u.id, company_id=ctx.company.id, role=body.role)
    s.add(m)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "anggota.set", f"{u.email} -> {body.role}")
    return {"ok": True}


@router.delete("/members/{user_id}")
def del_member(user_id: int, ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    m = s.exec(select(Membership).where(Membership.user_id == user_id, Membership.company_id == ctx.company.id)).first()
    if not m:
        raise HTTPException(404, "Anggota tidak ditemukan")
    s.delete(m)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "anggota.cabut", f"user {user_id}")
    return {"ok": True}


# ---- KBLI ----
def kbli_rows(ctx: Ctx):
    return [{"id": k.id, "code": k.code, "version": k.version, "name": k.name}
            for k in ctx.session.exec(select(CompanyKbli).where(CompanyKbli.company_id == ctx.company.id).order_by(CompanyKbli.code))]


@router.get("/kbli")
def get_kbli(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    op = kelayakan.kbli_openings(s, ctx.company.id)
    rows = kbli_rows(ctx)
    for r in rows:
        r["kategori_dibuka"] = op.get(f"{r['code']}|{r['version']}", 0)
    return {"kbli": rows, "ranking_tidak_bisa": kelayakan.kbli_ranking(s, ctx.company.id)}


@router.post("/kbli")
def add_kbli(body: KbliIn, ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    if body.version not in ("2020", "2025"):
        raise HTTPException(400, "Versi KBLI harus 2020 atau 2025")
    if s.exec(select(CompanyKbli).where(CompanyKbli.company_id == ctx.company.id, CompanyKbli.code == body.code,
                                        CompanyKbli.version == body.version)).first():
        raise HTTPException(409, "KBLI sudah ada")
    name = body.name or (s.exec(select(KbliName.name).where(KbliName.code == body.code, KbliName.version == body.version)).first() or "")
    s.add(CompanyKbli(company_id=ctx.company.id, code=body.code.strip(), version=body.version, name=name))
    s.commit()
    audit(s, ctx.user, ctx.company.id, "kbli.tambah", f"{body.code}|{body.version}")
    return {"ok": True}


@router.delete("/kbli/{kid}")
def del_kbli(kid: int, ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    k = s.get(CompanyKbli, kid)
    if not k or k.company_id != ctx.company.id:
        raise HTTPException(404, "KBLI tidak ditemukan")
    s.delete(k)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "kbli.hapus", f"{k.code}|{k.version}")
    return {"ok": True}


@router.post("/kbli/import-check")
async def import_check(file: UploadFile = File(...), ctx: Ctx = Depends(need("admin"))):
    """Impor inaproc_kbli_check.json (hasil scripts/browser_snippets.js). institutionId harus = perusahaan aktif."""
    s = ctx.session
    try:
        data = json.loads((await file.read()).decode("utf-8"))
    except Exception:
        raise HTTPException(400, "File bukan JSON yang valid")
    inst = data.get("institutionId")
    if inst != ctx.company.institution_id:
        raise HTTPException(
            400, f"institutionId di file ({inst}) tidak sama dengan perusahaan aktif ({ctx.company.institution_id}). "
                 "Jalankan snippet saat login ke akun INAPROC perusahaan ini.")
    from ..models import Category
    # KBLI perusahaan
    seller = data.get("seller") or []
    if seller:
        for k in s.exec(select(CompanyKbli).where(CompanyKbli.company_id == ctx.company.id)):
            s.delete(k)
        for it in seller:
            if isinstance(it, str):
                code, ver = it.split("|")
                name = ""
            else:
                code, ver, name = str(it.get("kode") or it.get("code")), str(it.get("versi") or it.get("version")), it.get("nama") or it.get("name") or ""
            s.add(CompanyKbli(company_id=ctx.company.id, code=code, version=ver, name=name))
    # UUID & kode KBLI kategori (global; cocokkan lewat path nama L1›L2›L3)
    idx = {(c.l1, c.l2, c.l3): c for c in kelayakan.all_categories(s)}
    n = 0
    for leaf in data.get("leaves") or data.get("categories") or []:
        c = idx.get((leaf.get("l1"), leaf.get("l2"), leaf.get("l3")))
        if c:
            # Data kategori bersifat global (dipakai semua perusahaan): hanya isi UUID yang masih kosong,
            # jangan menimpa kode KBLI kategori dari impor satu perusahaan.
            if leaf.get("id") and not c.uuid:
                c.uuid = leaf["id"]
                s.add(c)
            n += 1
    s.commit()
    kelayakan.invalidate()
    audit(s, ctx.user, ctx.company.id, "kbli.import", f"{n} kategori diperbarui")
    return {"ok": True, "kategori_diperbarui": n, "kbli": len(seller)}


# ---- dashboard & audit ----
@router.get("/dashboard")
def dashboard(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    cid = ctx.company.id
    tree = kelayakan.build_tree(s, cid)["totals"]
    by_status = {st: n for st, n in s.exec(select(Batch.status, func.count()).where(Batch.company_id == cid).group_by(Batch.status))}
    uploaded = s.exec(select(func.count()).select_from(ProductRow).join(Batch, Batch.id == ProductRow.batch_id)
                      .where(ProductRow.company_id == cid, Batch.status == "Sudah Diunggah")).one()
    existing = sum(kelayakan.existing_counts(s, cid).values())
    return {"kelayakan": tree, "batch": by_status, "produk_diunggah": uploaded, "produk_existing": existing,
            "peringatan_existing": kelayakan.existing_warnings(s, cid)}


@router.get("/audit")
def audit_log(limit: int = 200, ctx: Ctx = Depends(need("admin", "reviewer"))):
    q = select(AuditLog).where(AuditLog.company_id == ctx.company.id).order_by(AuditLog.id.desc()).limit(min(limit, 1000))
    return [{"id": a.id, "user": a.user_email, "action": a.action, "detail": a.detail, "ts": a.ts.isoformat()}
            for a in ctx.session.exec(q)]

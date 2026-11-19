"""Endpoint Fase 2 (AI): pengaturan, impor dokumen, job, konfirmasi Draf AI, aturan harga, pemakaian."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import func, select

from .. import config
from ..ai import ai_client, estimate as est, importer, jobs, models_registry as reg, parsers, settings as aset
from ..ai.service import CallCtx, ensure_ready
from ..deps import Ctx, any_member, audit, need, require_super
from ..db import get_session
from ..models import AiJob, AiUsage, Batch, CellSource, PricingRule, ProductRow, SourceDoc, User
from sqlmodel import Session

router = APIRouter(prefix="/api/companies/{company_id}/ai", tags=["ai"])
admin_router = APIRouter(prefix="/api/admin/ai", tags=["ai-admin"], dependencies=[Depends(require_super)])

MAX_FILE = 25 * 1024 * 1024
MAX_FILES = 10
CRITICAL = {"AC": "Harga", "X": "Stok", "R": "PDN produksi", "S": "PDN tenaga kerja", "T": "PDN bahan baku",
            "V": "Negara asal", "Q": "Kode KBKI", "kategori": "Kategori"}
PRIVACY = ("Dokumen dan foto supplier dikirim ke OpenRouter dan ke provider model yang dipakai (mis. Anthropic, Meta, ByteDance). "
           "Jangan unggah dokumen yang tidak boleh keluar dari perusahaan. Opsi 'tanpa penyimpanan data' hanya mengarahkan "
           "permintaan ke provider yang menyatakan tidak menyimpan data, bila tersedia untuk model itu.")


class SettingsIn(BaseModel):
    api_key: str | None = None
    clear_key: bool = False
    slots: dict | None = None
    quota_usd: float | None = None
    clear_quota: bool = False
    name_pattern: str | None = None
    no_data_retention: bool | None = None


class ImportIn(BaseModel):
    batch_id: int
    source_ids: list[int]
    ocr: bool = False
    hemat: bool = False


class ConfirmItem(BaseModel):
    row_id: int
    ack: list[str] = []


class ConfirmIn(BaseModel):
    items: list[ConfirmItem]


class RuleIn(BaseModel):
    scope: str = "semua"
    category_name: str = ""
    markup_pct: float = 0
    rounding: int = 0
    min_price: int = 0


# ---------- pengaturan ----------
def save_settings(s: Session, company_id: int | None, body: SettingsIn, user: User):
    row = aset.get_or_create(s, company_id)
    new_key = (body.api_key or "").strip()
    if body.slots:
        merged = {k: dict(v) for k, v in (row.slots or {}).items()}
        for slot, v in body.slots.items():
            if slot not in aset.SLOT_NAMES or not isinstance(v, dict):
                raise HTTPException(400, f"Slot tidak dikenal: {slot}")
            merged.setdefault(slot, {}).update({a: str(b or "").strip() for a, b in v.items() if a in ("model", "fallback")})
        # validasi kemampuan model terhadap daftar OpenRouter (wajib; tidak ada validasi = tidak boleh simpan)
        key = new_key or (aset.effective(s, company_id)["api_key"] if company_id else aset.decrypt(row.api_key_enc))
        if not key:
            raise HTTPException(400, "Isi API key OpenRouter dulu agar model bisa divalidasi.")
        try:
            registry = reg.load(key, force=True)
        except ai_client.AiError as e:
            raise HTTPException(400, f"Tidak bisa memvalidasi model: {e}")
        errs = []
        for slot, v in merged.items():
            for fld in ("model", "fallback"):
                m = v.get(fld)
                if m and (body.slots.get(slot) or {}).get(fld) is not None:
                    e = reg.validate_slot(registry, slot, m)
                    if e:
                        errs.append(e)
        if errs:
            raise HTTPException(400, {"pesan": "Model ditolak", "detail": errs})
        row.slots = merged
    if new_key:
        row.api_key_enc = aset.encrypt(new_key)
    if body.clear_key:
        row.api_key_enc = ""
    if body.clear_quota:
        row.quota_usd = None
    elif body.quota_usd is not None:
        if body.quota_usd < 0:
            raise HTTPException(400, "Kuota tidak boleh negatif")
        row.quota_usd = body.quota_usd
    if body.name_pattern is not None and body.name_pattern.strip():
        row.name_pattern = body.name_pattern.strip()[:200]
    if body.no_data_retention is not None:
        row.no_data_retention = body.no_data_retention
    row.updated_at = datetime.now(timezone.utc)
    s.add(row)
    s.commit()
    # catat tanpa nilai key
    changed = [k for k, v in (("api_key", bool(new_key)), ("slots", bool(body.slots)), ("kuota", body.quota_usd is not None or body.clear_quota),
                              ("pola_nama", body.name_pattern is not None), ("tanpa_retensi", body.no_data_retention is not None)) if v]
    audit(s, user, company_id, "ai.pengaturan", ",".join(changed))


@router.get("/settings")
def get_settings(ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    eff = aset.effective(s, ctx.company.id)
    return {**aset.public_view(s, ctx.company.id), "key_source": eff["key_source"], "efektif": {"slots": eff["slots"]},
            "kuota_status": aset.quota_status(s, ctx.company.id), "privasi": PRIVACY}


@router.put("/settings")
def put_settings(body: SettingsIn, ctx: Ctx = Depends(need("admin"))):
    save_settings(ctx.session, ctx.company.id, body, ctx.user)
    return get_settings(ctx)


@router.get("/models")
def list_models(slot: str | None = None, ctx: Ctx = Depends(need("admin"))):
    key = aset.effective(ctx.session, ctx.company.id)["api_key"]
    if not key:
        raise HTTPException(400, "Isi API key OpenRouter dulu.")
    try:
        return reg.listing(reg.load(key), slot)
    except ai_client.AiError as e:
        raise HTTPException(502, str(e))


@router.get("/status")
def status(ctx: Ctx = Depends(any_member)):
    eff = aset.effective(ctx.session, ctx.company.id)
    return {"siap": bool(eff["api_key"]), "kuota": aset.quota_status(ctx.session, ctx.company.id)}


# ---------- Super Admin: pengaturan organisasi ----------
@admin_router.get("")
def admin_get(s: Session = Depends(get_session)):
    return {**aset.public_view(s, None), "privasi": PRIVACY}


@admin_router.put("")
def admin_put(body: SettingsIn, user: User = Depends(require_super), s: Session = Depends(get_session)):
    save_settings(s, None, body, user)
    return {**aset.public_view(s, None), "privasi": PRIVACY}


# ---------- dokumen sumber & impor ----------
def _editable_batch(ctx: Ctx, bid: int) -> Batch:
    b = ctx.session.get(Batch, bid)
    if not b or b.company_id != ctx.company.id:
        raise HTTPException(404, "Batch tidak ditemukan")
    if b.status not in ("Draft", "Perlu Perbaikan"):
        raise HTTPException(409, f"Batch berstatus '{b.status}' dan tidak bisa diubah")
    return b


@router.post("/sources")
async def upload_sources(batch_id: int = Form(...), ocr: bool = Form(False), files: list[UploadFile] = File(...),
                         ctx: Ctx = Depends(need("admin", "operator"))):
    s = ctx.session
    _editable_batch(ctx, batch_id)
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Maksimal {MAX_FILES} file per unggahan")
    d = config.STORAGE_DIR / f"company_{ctx.company.id}" / "sources"
    d.mkdir(parents=True, exist_ok=True)
    docs, rejected = [], []
    for f in files:
        kind = parsers.kind_of(f.filename or "")
        raw = await f.read()
        if not kind:
            rejected.append({"file": f.filename, "alasan": "Jenis file tidak didukung (Excel, CSV, PDF, atau gambar)."})
            continue
        if len(raw) > MAX_FILE:
            rejected.append({"file": f.filename, "alasan": "Ukuran lebih dari 25 MB."})
            continue
        sha = hashlib.sha256(raw).hexdigest()
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (f.filename or "file"))
        path = d / f"{sha[:12]}_{safe}"
        path.write_bytes(raw)
        doc = SourceDoc(company_id=ctx.company.id, batch_id=batch_id, filename=f.filename, kind=kind, path=str(path),
                        size=len(raw), sha256=sha, uploaded_by=ctx.user.id)
        s.add(doc)
        s.commit()
        s.refresh(doc)
        docs.append(doc)
    return {"docs": [{"id": x.id, "filename": x.filename, "kind": x.kind, "size": x.size} for x in docs], "ditolak": rejected,
            "estimasi": est.estimate(s, ctx.company.id, docs, ocr) if docs else None}


def _job_dict(j: AiJob) -> dict:
    return {"id": j.id, "kind": j.kind, "status": j.status, "progress": j.progress, "message": j.message, "result": j.result,
            "batch_id": j.batch_id, "created_at": j.created_at.isoformat(), "finished_at": j.finished_at.isoformat() if j.finished_at else None}


@router.post("/import")
def start_import(body: ImportIn, ctx: Ctx = Depends(need("admin", "operator"))):
    s = ctx.session
    _editable_batch(ctx, body.batch_id)
    docs = [s.get(SourceDoc, i) for i in body.source_ids]
    if not docs or any(d is None or d.company_id != ctx.company.id for d in docs):
        raise HTTPException(404, "Dokumen sumber tidak ditemukan")
    try:
        ensure_ready(s, CallCtx(ctx.company.id, ctx.user.id, body.batch_id))
    except ai_client.AiQuotaExceeded as e:
        raise HTTPException(402, str(e))
    except ai_client.AiError as e:
        raise HTTPException(400, str(e))
    job = AiJob(company_id=ctx.company.id, batch_id=body.batch_id, user_id=ctx.user.id, kind="impor",
                params={"source_ids": body.source_ids, "ocr": body.ocr, "hemat": body.hemat})
    s.add(job)
    s.commit()
    s.refresh(job)
    audit(s, ctx.user, ctx.company.id, "ai.impor_mulai", f"batch #{body.batch_id}, {len(docs)} dokumen")
    jobs.submit(job.id, importer.run_import)
    s.refresh(job)
    return _job_dict(job)


@router.get("/jobs/{jid}")
def get_job(jid: int, ctx: Ctx = Depends(any_member)):
    j = ctx.session.get(AiJob, jid)
    if not j or j.company_id != ctx.company.id:
        raise HTTPException(404, "Job tidak ditemukan")
    return _job_dict(j)


@router.get("/jobs")
def list_jobs(batch_id: int | None = None, ctx: Ctx = Depends(any_member)):
    q = select(AiJob).where(AiJob.company_id == ctx.company.id).order_by(AiJob.id.desc()).limit(30)
    if batch_id:
        q = q.where(AiJob.batch_id == batch_id)
    return [_job_dict(j) for j in ctx.session.exec(q)]


# ---------- konfirmasi Draf AI (hanya Operator/Admin; Reviewer tidak) ----------
def required_ack(row: ProductRow) -> list:
    return [k for k in CRITICAL if k == "kategori" or row.data.get(k) not in (None, "")]


@router.post("/batches/{bid}/confirm")
def confirm_rows(bid: int, body: ConfirmIn, ctx: Ctx = Depends(need("admin", "operator"))):
    s = ctx.session
    b = _editable_batch(ctx, bid)
    done, problems = [], []
    for it in body.items:
        r = s.get(ProductRow, it.row_id)
        if not r or r.batch_id != b.id or r.company_id != ctx.company.id:
            raise HTTPException(404, f"Baris {it.row_id} tidak ditemukan di batch ini")
        if r.origin != "Draf AI":
            continue
        miss = [CRITICAL[k] for k in required_ack(r) if k not in it.ack]
        if miss:
            problems.append(f"Baris {r.data.get('D', r.id)}: konfirmasi eksplisit {', '.join(miss)}")
            continue
        r.confirmed_by, r.confirmed_at, r.confirmed_ack = ctx.user.id, datetime.now(timezone.utc), sorted(it.ack)
        s.add(r)
        done.append(r.id)
    s.commit()
    if done:
        audit(s, ctx.user, ctx.company.id, "ai.konfirmasi", f"batch #{b.id}: {len(done)} baris")
    if problems and not done:
        raise HTTPException(422, {"pesan": "Kolom kritis belum dikonfirmasi", "detail": problems})
    return {"dikonfirmasi": done, "ditolak": problems}


@router.get("/critical")
def critical(ctx: Ctx = Depends(any_member)):
    return CRITICAL


# ---------- aturan harga ----------
def _rule_dict(r: PricingRule) -> dict:
    return {"id": r.id, "scope": r.scope, "category_name": r.category_name, "markup_pct": r.markup_pct, "rounding": r.rounding, "min_price": r.min_price}


@router.get("/pricing-rules")
def list_rules(ctx: Ctx = Depends(any_member)):
    return [_rule_dict(r) for r in ctx.session.exec(select(PricingRule).where(PricingRule.company_id == ctx.company.id).order_by(PricingRule.id))]


@router.post("/pricing-rules")
def add_rule(body: RuleIn, ctx: Ctx = Depends(need("admin"))):
    if body.scope not in ("semua", "l1", "l2", "l3"):
        raise HTTPException(400, "Cakupan harus semua/l1/l2/l3")
    if body.scope != "semua" and not body.category_name.strip():
        raise HTTPException(400, "Nama kategori wajib untuk cakupan ini")
    if body.markup_pct < 0 or body.rounding < 0 or body.min_price < 0:
        raise HTTPException(400, "Nilai tidak boleh negatif")
    r = PricingRule(company_id=ctx.company.id, **{**body.model_dump(), "category_name": body.category_name.strip()})
    ctx.session.add(r)
    ctx.session.commit()
    ctx.session.refresh(r)
    audit(ctx.session, ctx.user, ctx.company.id, "ai.aturan_harga", f"+{r.scope}:{r.category_name} {r.markup_pct}%")
    return _rule_dict(r)


@router.delete("/pricing-rules/{rid}")
def del_rule(rid: int, ctx: Ctx = Depends(need("admin"))):
    r = ctx.session.get(PricingRule, rid)
    if not r or r.company_id != ctx.company.id:
        raise HTTPException(404, "Aturan tidak ditemukan")
    ctx.session.delete(r)
    ctx.session.commit()
    return {"ok": True}


# ---------- pemakaian ----------
@router.get("/usage")
def usage(ctx: Ctx = Depends(need("admin", "reviewer"))):
    s = ctx.session
    cid = ctx.company.id
    rows = s.exec(select(AiUsage.slot, AiUsage.model, func.count(), func.sum(AiUsage.prompt_tokens), func.sum(AiUsage.completion_tokens),
                         func.sum(AiUsage.cost_usd)).where(AiUsage.company_id == cid, AiUsage.ts >= aset.month_start()).group_by(AiUsage.slot, AiUsage.model)).all()
    draf = s.exec(select(func.count()).select_from(ProductRow).where(ProductRow.company_id == cid, ProductRow.origin == "Draf AI")).one()
    return {"kuota": aset.quota_status(s, cid),
            "per_model": [{"slot": a, "model": b, "panggilan": c, "token_masuk": int(d or 0), "token_keluar": int(e or 0), "biaya_usd": round(float(f or 0), 5)} for a, b, c, d, e, f in rows],
            "baris_draf_ai": draf}


def sources_for_batch(s: Session, company_id: int, row_ids: list) -> dict:
    """{row_id: {kolom: {file, lokasi, kutipan, terverifikasi}}} untuk tooltip di grid."""
    out: dict = {}
    if not row_ids:
        return out
    for c in s.exec(select(CellSource).where(CellSource.company_id == company_id, CellSource.row_id.in_(row_ids))):
        out.setdefault(c.row_id, {})[c.col] = {"file": c.doc_name, "lokasi": c.location, "kutipan": c.quote, "terverifikasi": c.verified}
    return out

"""Batch produk: grid input, validasi, alur status, review, ekspor zip."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select

from .. import config
from ..deps import Ctx, any_member, audit, need
from ..models import Batch, Photo, ProductRow, TemplateSchema, UploadHistory, User
from ..services import exporter
from ..services.defaults import apply_defaults
from ..services.form_io import import_form
from ..services.validator import PHOTO_COLS, empty, prepare_ctx, resolve_photo, validate_row

router = APIRouter(prefix="/api/companies/{company_id}/batches", tags=["batch"])

EDITABLE = ("Draft", "Perlu Perbaikan")
WARNING_EXPORT = "Produk akan langsung TAYANG dan bisa dibeli setelah diunggah. Unggahan tidak bisa dibatalkan."
DUMMY = "[DUMMY] "


class BatchIn(BaseModel):
    name: str
    is_test: bool = False
    pdn_preset: str = "Lokal"


class RowIn(BaseModel):
    id: int | None = None
    schema_id: int | None = None
    data: dict = {}


class RowsIn(BaseModel):
    rows: list[RowIn] = []
    delete_ids: list[int] = []


class ExportIn(BaseModel):
    confirm: bool = False
    placeholder_url: str | None = None


class HistoryIn(BaseModel):
    file_name: str = ""
    result: str = "berhasil"
    message: str = ""
    row_ids: list[int] = []
    reopen: bool = False


def get_batch(ctx: Ctx, bid: int) -> Batch:
    b = ctx.session.get(Batch, bid)
    if not b or b.company_id != ctx.company.id:   # lintas perusahaan -> 404
        raise HTTPException(404, "Batch tidak ditemukan")
    return b


def schemas_of(ctx: Ctx) -> dict:
    return {t.id: t for t in ctx.session.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id))}


def rows_of(ctx: Ctx, b: Batch) -> list:
    return list(ctx.session.exec(select(ProductRow).where(ProductRow.batch_id == b.id, ProductRow.company_id == ctx.company.id)
                                 .order_by(ProductRow.position, ProductRow.id)))


def photos_of(ctx: Ctx, b: Batch) -> list:
    return list(ctx.session.exec(select(Photo).where(Photo.batch_id == b.id, Photo.company_id == ctx.company.id)))


def existing_names(ctx: Ctx, b: Batch) -> set:
    from ..services.validator import norm_name
    s = ctx.session
    ids = [x.id for x in s.exec(select(Batch).where(Batch.company_id == ctx.company.id, Batch.id != b.id,
                                                    Batch.status.in_(("Diekspor", "Sudah Diunggah"))))]
    out = set()
    if ids:
        for r in s.exec(select(ProductRow).where(ProductRow.company_id == ctx.company.id, ProductRow.batch_id.in_(ids))):
            out.add(norm_name(r.data.get("D")))
    return out


def batch_dict(b: Batch, s=None) -> dict:
    d = b.model_dump(mode="json")
    if s is not None:
        d["n_produk"] = len(s.exec(select(ProductRow.id).where(ProductRow.batch_id == b.id)).all())
        u = s.get(User, b.created_by)
        d["dibuat_oleh"] = u.email if u else ""
    return d


def evaluate(ctx: Ctx, b: Batch):
    """Validasi seluruh baris. Mengembalikan (rows_out, ringkasan)."""
    schemas = schemas_of(ctx)
    rows = rows_of(ctx, b)
    photos = photos_of(ctx, b)
    vctx = prepare_ctx(rows, photos, existing_names(ctx, b))
    out, n_err, n_warn, guess, no_link, n_draf = [], 0, 0, 0, 0, 0
    per_cat: dict = {}
    warnings = []
    for r in rows:
        sc = schemas.get(r.schema_id)
        if not sc:
            issues = [{"col": "kategori", "level": "error", "msg": "Pilih kategori yang punya template"}]
        else:
            issues = validate_row(sc, r.data, vctx)
        e = sum(1 for i in issues if i["level"] == "error")
        w = sum(1 for i in issues if i["level"] == "warn")
        n_err += e
        n_warn += w
        if r.kbki_guess:
            guess += 1
            warnings.append({"row_id": r.id, "nama": r.data.get("D", ""), "msg": "KBKI hasil tebakan — mohon dicek"})
        if sc and not empty(r.data.get("E")) and not resolve_photo(r.data.get("E"), vctx.photos):
            no_link += 1
            warnings.append({"row_id": r.id, "nama": r.data.get("D", ""), "msg": "Foto utama belum punya link publik .png"})
        if sc:
            pc = per_cat.setdefault(sc.category_name, {"jumlah": 0, "harga_min": None, "harga_max": None})
            pc["jumlah"] += 1
            try:
                h = int(float(str(r.data.get("AC")).replace(".", "").replace(",", ""))) if not empty(r.data.get("AC")) else None
            except ValueError:
                h = None
            if h:
                pc["harga_min"] = h if pc["harga_min"] is None else min(pc["harga_min"], h)
                pc["harga_max"] = h if pc["harga_max"] is None else max(pc["harga_max"], h)
        draf = r.origin == "Draf AI"
        if draf and not r.confirmed_at:
            n_draf += 1
        out.append({"id": r.id, "schema_id": r.schema_id, "position": r.position, "data": r.data,
                    "kbki_guess": r.kbki_guess, "issues": issues,
                    "upload_status": r.upload_status, "upload_message": r.upload_message,
                    "origin": r.origin or "Manual", "confirmed": bool(r.confirmed_at), "ai_meta": r.ai_meta if draf else {}})
    summ = {"total": len(rows), "error": n_err, "warn": n_warn, "kbki_tebakan": guess, "foto_tanpa_link": no_link,
            "per_kategori": per_cat, "peringatan": warnings,
            "baris_error": sum(1 for o in out if any(i["level"] == "error" for i in o["issues"])),
            "draf_belum_konfirmasi": n_draf}
    return out, summ


def sanitize(sc: TemplateSchema, data: dict, b: Batch) -> dict:
    """Hanya kolom yang ada di skema; kolom (Kosongkan)/otomatis/sistem dan U dipaksa kosong."""
    allowed = {c["letter"] for c in sc.columns if c["req"] not in ("kosongkan", "otomatis", "sistem")} - {"U", "C"}
    out = {}
    for k, v in (data or {}).items():
        if k not in allowed:
            continue
        if isinstance(v, str):
            v = v.strip()
        if v in (None, ""):
            continue
        out[k] = v
    if b.is_test and out.get("D") and not str(out["D"]).startswith("[DUMMY]"):
        out["D"] = DUMMY + str(out["D"])
    return out


def touch(ctx: Ctx, b: Batch):
    b.updated_at = datetime.now(timezone.utc)
    ctx.session.add(b)


def need_editable(b: Batch):
    if b.status not in EDITABLE:
        raise HTTPException(409, f"Batch berstatus '{b.status}' dan tidak bisa diubah. Kembalikan ke perbaikan dulu.")


def set_status(ctx: Ctx, b: Batch, new: str, detail: str = ""):
    old = b.status
    b.status = new
    touch(ctx, b)
    ctx.session.commit()
    audit(ctx.session, ctx.user, ctx.company.id, "batch.status", f"#{b.id} {old} → {new} {detail}".strip())


# ---------- CRUD ----------
@router.get("")
def list_batches(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    rows = s.exec(select(Batch).where(Batch.company_id == ctx.company.id).order_by(Batch.id.desc())).all()
    return [batch_dict(b, s) for b in rows]


@router.post("")
def create_batch(body: BatchIn, ctx: Ctx = Depends(need("admin", "operator"))):
    if not body.name.strip():
        raise HTTPException(400, "Nama batch wajib")
    if body.pdn_preset not in ("Lokal", "Impor"):
        raise HTTPException(400, "Preset PDN harus Lokal atau Impor")
    name = body.name.strip()
    if body.is_test and not name.startswith("[DUMMY]"):
        name = DUMMY + name
    b = Batch(company_id=ctx.company.id, name=name, is_test=body.is_test, pdn_preset=body.pdn_preset, created_by=ctx.user.id)
    ctx.session.add(b)
    ctx.session.commit()
    ctx.session.refresh(b)
    audit(ctx.session, ctx.user, ctx.company.id, "batch.buat", f"#{b.id} {b.name}")
    return batch_dict(b, ctx.session)


@router.get("/{bid}")
def get_one(bid: int, ctx: Ctx = Depends(any_member)):
    b = get_batch(ctx, bid)
    rows, summ = evaluate(ctx, b)
    reviewer = ctx.session.get(User, b.reviewed_by).email if b.reviewed_by else ""
    from .ai import sources_for_batch
    return {"batch": batch_dict(b, ctx.session), "rows": rows, "ringkasan": summ, "reviewer": reviewer,
            "sumber": sources_for_batch(ctx.session, ctx.company.id, [r["id"] for r in rows if r["origin"] == "Draf AI"]),
            "photos": [{"id": p.id, "row_id": p.row_id, "filename": p.filename, "public_url": p.public_url,
                        "width": p.width, "height": p.height, "size": p.size, "kind": p.kind} for p in photos_of(ctx, b)]}


@router.patch("/{bid}")
def patch_batch(bid: int, body: dict, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    need_editable(b)
    if "name" in body and str(body["name"]).strip():
        b.name = str(body["name"]).strip()
    if body.get("pdn_preset") in ("Lokal", "Impor"):
        b.pdn_preset = body["pdn_preset"]
    if "is_test" in body:
        b.is_test = bool(body["is_test"])
    touch(ctx, b)
    ctx.session.commit()
    return batch_dict(b, ctx.session)


@router.delete("/{bid}")
def delete_batch(bid: int, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    if b.status != "Draft":
        raise HTTPException(409, "Hanya batch Draft yang bisa dihapus")
    if ctx.role != "admin" and b.created_by != ctx.user.id:
        raise HTTPException(403, "Hanya pembuat batch atau Admin yang bisa menghapus")
    s = ctx.session
    for model in (ProductRow, Photo, UploadHistory):
        for x in s.exec(select(model).where(model.batch_id == b.id)):
            s.delete(x)
    s.delete(b)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "batch.hapus", f"#{bid}")
    return {"ok": True}


# ---------- baris ----------
@router.put("/{bid}/rows")
def save_rows(bid: int, body: RowsIn, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    need_editable(b)
    s = ctx.session
    schemas = schemas_of(ctx)
    existing = {r.id: r for r in rows_of(ctx, b)}
    for did in body.delete_ids:
        r = existing.get(did)
        if r:
            s.delete(r)
    pos = max([r.position for r in existing.values()] + [0])
    for item in body.rows:
        row = existing.get(item.id) if item.id else None
        if item.id and not row:
            raise HTTPException(404, f"Baris {item.id} tidak ditemukan di batch ini")
        sid = item.schema_id or (row.schema_id if row else None)
        sc = schemas.get(sid) if sid else None
        if sid and not sc:   # template milik perusahaan lain / tidak ada
            raise HTTPException(404, "Template/kategori tidak ditemukan di perusahaan ini")
        if row:
            changed_schema = sc is not None and row.schema_id != sid
            cur = {} if changed_schema else dict(row.data)
            if sc:
                clean = sanitize(sc, item.data, b)
                # sel yang dikosongkan oleh pengguna harus benar-benar terhapus
                for k, v in item.data.items():
                    if empty(v):
                        cur.pop(k, None)
                if "Q" in clean and clean["Q"] != row.data.get("Q"):
                    row.kbki_guess = False
                cur.update(clean)
                if changed_schema:
                    cur, row.kbki_guess = apply_defaults(sc, cur, b.pdn_preset)
                row.schema_id = sid
            row.data = cur
            s.add(row)
        else:
            pos += 1
            data, guess = {}, False
            if sc:
                data, guess = apply_defaults(sc, sanitize(sc, item.data, b), b.pdn_preset)
            s.add(ProductRow(company_id=ctx.company.id, batch_id=b.id, schema_id=item.schema_id, position=pos,
                             data=data, kbki_guess=guess))
    touch(ctx, b)
    s.commit()
    rows, summ = evaluate(ctx, b)
    return {"rows": rows, "ringkasan": summ}


@router.post("/{bid}/import-form")
async def import_form_endpoint(bid: int, file: UploadFile = File(...), ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    need_editable(b)
    try:
        rows, issues = import_form(await file.read(), list(schemas_of(ctx).values()))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Form tidak bisa dibaca: {e}")
    s = ctx.session
    pos = max([r.position for r in rows_of(ctx, b)] + [0])
    for sc, d in rows:
        pos += 1
        data, guess = apply_defaults(sc, sanitize(sc, d, b), b.pdn_preset)
        s.add(ProductRow(company_id=ctx.company.id, batch_id=b.id, schema_id=sc.id, position=pos, data=data, kbki_guess=guess))
    touch(ctx, b)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "batch.impor_form", f"#{b.id}: {len(rows)} baris")
    return {"diimpor": len(rows), "dilewati": issues}


@router.get("/{bid}/validate")
def validate_batch(bid: int, ctx: Ctx = Depends(any_member)):
    rows, summ = evaluate(ctx, get_batch(ctx, bid))
    return {"rows": rows, "ringkasan": summ}


# ---------- alur status ----------
@router.post("/{bid}/submit")
def submit(bid: int, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    need_editable(b)
    _rows, summ = evaluate(ctx, b)
    if summ["total"] == 0:
        raise HTTPException(422, "Batch kosong")
    if summ["error"]:
        raise HTTPException(422, f"Masih ada {summ['error']} error validasi pada {summ['baris_error']} baris — perbaiki dulu")
    if summ["draf_belum_konfirmasi"]:
        raise HTTPException(422, f"Ada {summ['draf_belum_konfirmasi']} baris Draf AI yang belum dikonfirmasi Operator")
    set_status(ctx, b, "Diajukan")
    return batch_dict(b, ctx.session)


class NoteIn(BaseModel):
    note: str = ""


@router.post("/{bid}/approve")
def approve(bid: int, ctx: Ctx = Depends(need("reviewer"))):
    b = get_batch(ctx, bid)
    if b.status != "Diajukan":
        raise HTTPException(409, "Hanya batch berstatus Diajukan yang bisa disetujui")
    if b.created_by == ctx.user.id:
        raise HTTPException(403, "Reviewer tidak boleh menyetujui batch yang ia buat sendiri")
    _rows, summ = evaluate(ctx, b)
    if summ["error"]:
        raise HTTPException(422, "Batch masih memiliki error validasi")
    if summ["draf_belum_konfirmasi"]:
        raise HTTPException(422, "Masih ada baris Draf AI yang belum dikonfirmasi Operator")
    b.reviewed_by, b.review_note = ctx.user.id, ""
    set_status(ctx, b, "Disetujui")
    return batch_dict(b, ctx.session)


@router.post("/{bid}/return")
def return_batch(bid: int, body: NoteIn, ctx: Ctx = Depends(need("reviewer"))):
    b = get_batch(ctx, bid)
    if b.status not in ("Diajukan", "Disetujui"):
        raise HTTPException(409, "Hanya batch Diajukan/Disetujui yang bisa dikembalikan")
    if b.created_by == ctx.user.id:
        raise HTTPException(403, "Reviewer tidak boleh me-review batch yang ia buat sendiri")
    if not body.note.strip():
        raise HTTPException(400, "Catatan wajib diisi saat mengembalikan batch")
    b.reviewed_by, b.review_note = ctx.user.id, body.note.strip()
    set_status(ctx, b, "Perlu Perbaikan", body.note.strip()[:200])
    return batch_dict(b, ctx.session)


# ---------- ekspor ----------
def export_dir(ctx: Ctx, b: Batch):
    p = config.STORAGE_DIR / f"company_{ctx.company.id}" / "exports" / f"batch_{b.id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.post("/{bid}/export")
def export_batch(bid: int, body: ExportIn, ctx: Ctx = Depends(need("admin", "reviewer"))):
    b = get_batch(ctx, bid)
    if b.status not in ("Disetujui", "Diekspor"):
        raise HTTPException(403, "Ekspor hanya untuk batch yang sudah Disetujui Reviewer")
    if not body.confirm:
        raise HTTPException(400, WARNING_EXPORT + " Centang konfirmasi untuk melanjutkan.")
    rows, summ = evaluate(ctx, b)
    if summ["error"]:
        raise HTTPException(422, "Batch masih memiliki error validasi")
    schemas = schemas_of(ctx)
    photos = {p.filename.lower(): p for p in photos_of(ctx, b)}
    status = "Tidak Tayang" if b.is_test else "Tayang"
    placeholder = (body.placeholder_url or "").strip() if b.is_test else ""
    if placeholder and not re.match(r"^https?://\S+\.png$", placeholder, re.I):
        raise HTTPException(400, "Link contoh harus berakhiran .png")
    by_schema: dict = {}
    problems = []
    for r in rows:
        sc = schemas[r["schema_id"]]
        if sc.institution_id != ctx.company.institution_id:
            raise HTTPException(422, f"Template '{sc.category_name}' bukan milik perusahaan aktif")
        d = dict(r["data"])
        for k in PHOTO_COLS:
            if not empty(d.get(k)) and not resolve_photo(d[k], photos):
                if placeholder:
                    d[k] = placeholder
                else:
                    problems.append(f"'{d.get('D')}': foto {k} belum punya link publik .png")
        by_schema.setdefault(sc.id, (sc, []))[1].append(d)
    if problems:
        raise HTTPException(422, {"pesan": "Tempel link publik foto dulu sebelum ekspor", "detail": problems[:50]})
    files, items = [], []
    for sc, data_rows in by_schema.values():
        files.append((sc.filename, exporter.fill_template(sc, data_rows, status, photos)))
        for d in data_rows:
            items.append((sc.category_name, d.get("D"), d.get("AC"), d.get("Q")))
    # semua file harus ber-Institution ID perusahaan aktif
    from openpyxl import load_workbook
    import io
    for name, data in files:
        if str(load_workbook(io.BytesIO(data)).worksheets[0]["B1"].value) != ctx.company.institution_id:
            raise HTTPException(422, f"{name}: Institution ID tidak cocok dengan perusahaan aktif")
    d = export_dir(ctx, b)
    for old in d.glob("*"):
        old.unlink()
    base = f"unggah_inaproc_batch{b.id}"
    zips = exporter.pack_zips(files, base)
    for name, data in zips:
        (d / name).write_bytes(data)
    warn = [(w["nama"], w["msg"]) for w in summ["peringatan"]]
    (d / "laporan_batch.xlsx").write_bytes(exporter.build_report(b, ctx.company, items, warn))
    if b.status != "Diekspor":
        set_status(ctx, b, "Diekspor")
    audit(ctx.session, ctx.user, ctx.company.id, "batch.ekspor", f"#{b.id}: {len(files)} file, {len(zips)} zip")
    out = [{"name": n, "size": len(x), "url": f"/api/companies/{ctx.company.id}/batches/{b.id}/exports/{n}"} for n, x in zips]
    rep = d / "laporan_batch.xlsx"
    out.append({"name": rep.name, "size": rep.stat().st_size, "url": f"/api/companies/{ctx.company.id}/batches/{b.id}/exports/{rep.name}"})
    return {"files": out, "status_produk": status, "peringatan": WARNING_EXPORT,
            "pengingat_uji": "Hapus produk dummy dari INAPROC segera setelah tes." if b.is_test else ""}


@router.get("/{bid}/exports/{filename}")
def download_export(bid: int, filename: str, ctx: Ctx = Depends(need("admin", "reviewer"))):
    b = get_batch(ctx, bid)
    if not re.match(r"^[\w.\-]+$", filename):
        raise HTTPException(400, "Nama file tidak valid")
    p = export_dir(ctx, b) / filename
    if not p.is_file():
        raise HTTPException(404, "File belum dibuat — ekspor dulu")
    return FileResponse(p, filename=filename)


# ---------- riwayat unggah ----------
@router.get("/{bid}/history")
def history(bid: int, ctx: Ctx = Depends(any_member)):
    b = get_batch(ctx, bid)
    return [{"id": h.id, "file_name": h.file_name, "result": h.result, "message": h.message, "ts": h.ts.isoformat()}
            for h in ctx.session.exec(select(UploadHistory).where(UploadHistory.batch_id == b.id,
                                                                  UploadHistory.company_id == ctx.company.id).order_by(UploadHistory.id.desc()))]


@router.post("/{bid}/history")
def add_history(bid: int, body: HistoryIn, ctx: Ctx = Depends(any_member)):
    """Catat hasil unggah manual di INAPROC. Gagal + row_ids -> baris dibuka kembali untuk diperbaiki."""
    b = get_batch(ctx, bid)
    if b.status not in ("Diekspor", "Sudah Diunggah", "Perlu Perbaikan"):
        raise HTTPException(409, "Catat riwayat setelah batch diekspor")
    if body.result not in ("berhasil", "gagal"):
        raise HTTPException(400, "Hasil harus berhasil/gagal")
    s = ctx.session
    s.add(UploadHistory(company_id=ctx.company.id, batch_id=b.id, file_name=body.file_name, result=body.result,
                        message=body.message, user_id=ctx.user.id))
    mine = {r.id: r for r in rows_of(ctx, b)}
    for rid in body.row_ids:
        r = mine.get(rid)
        if r:
            r.upload_status, r.upload_message = body.result, body.message
            s.add(r)
    s.commit()
    if body.result == "gagal" and body.reopen:
        b.review_note = f"Gagal unggah: {body.message}"[:500]
        set_status(ctx, b, "Perlu Perbaikan", "dibuka kembali setelah gagal unggah")
    audit(s, ctx.user, ctx.company.id, "batch.riwayat", f"#{b.id} {body.result}")
    return {"ok": True}


@router.post("/{bid}/mark-uploaded")
def mark_uploaded(bid: int, body: NoteIn, ctx: Ctx = Depends(any_member)):
    b = get_batch(ctx, bid)
    if b.status != "Diekspor":
        raise HTTPException(409, "Hanya batch Diekspor yang bisa ditandai Sudah Diunggah")
    ctx.session.add(UploadHistory(company_id=ctx.company.id, batch_id=b.id, file_name="", result="berhasil",
                                  message=body.note, user_id=ctx.user.id))
    set_status(ctx, b, "Sudah Diunggah", body.note[:200])
    return batch_dict(b, ctx.session)

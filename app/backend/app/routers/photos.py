"""Foto produk & banner jasa per batch."""
import io
import re
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import select

from .. import config
from ..deps import Ctx, any_member, need
from ..models import Batch, Photo, ProductRow
from ..services import photos as ph
from ..services.validator import PNG_RE, norm_name
from .batches import EDITABLE, get_batch, photos_of, rows_of

router = APIRouter(prefix="/api/companies/{company_id}/batches/{bid}", tags=["foto"])


class BannerIn(BaseModel):
    title: str
    points: list[str] = []
    company: str | None = None
    row_id: int | None = None


def pdir(ctx: Ctx, b: Batch):
    p = config.STORAGE_DIR / f"company_{ctx.company.id}" / "photos" / f"batch_{b.id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def match_row(filename: str, rows: list):
    """Cocokkan foto ke baris: nama file sama dengan isi kolom foto, atau nama file (tanpa ekstensi) memuat/dimuat nama produk."""
    low = filename.lower()
    stem = slug(low.rsplit(".", 1)[0])
    for r in rows:
        for k in ("E", "F", "G", "H", "I"):
            if str(r.data.get(k) or "").strip().lower() == low:
                return r
    for r in rows:
        n = slug(str(r.data.get("D") or ""))
        if n and (stem == n or stem.startswith(n) or n.startswith(stem) and len(stem) >= 6):
            return r
    return None


def photo_dict(p: Photo) -> dict:
    return {"id": p.id, "row_id": p.row_id, "filename": p.filename, "public_url": p.public_url,
            "width": p.width, "height": p.height, "size": p.size, "kind": p.kind}


@router.post("/photos")
async def upload_photos(bid: int, files: list[UploadFile] = File(...), crop: bool = Form(False),
                        ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    if b.status not in EDITABLE:
        raise HTTPException(409, "Batch tidak bisa diubah pada status ini")
    s = ctx.session
    rows = rows_of(ctx, b)
    out, errors = [], []
    for f in files:
        try:
            data, w, h = ph.process_image(await f.read(), crop=crop)
        except ph.PhotoError as e:
            errors.append({"file": f.filename, "alasan": str(e)})
            continue
        name = f.filename.rsplit(".", 1)[0] + ".png"
        row = match_row(f.filename, rows) or match_row(name, rows)
        path = pdir(ctx, b) / f"{uuid.uuid4().hex}.png"
        path.write_bytes(data)
        # ganti foto lama dengan nama sama
        for old in s.exec(select(Photo).where(Photo.batch_id == b.id, Photo.filename == name)):
            try:
                open(old.path, "rb").close()
                import os
                os.remove(old.path)
            except OSError:
                pass
            s.delete(old)
        p = Photo(company_id=ctx.company.id, batch_id=b.id, row_id=row.id if row else None, filename=name,
                  path=str(path), width=w, height=h, size=len(data))
        s.add(p)
        s.commit()
        s.refresh(p)
        out.append({**photo_dict(p), "cocok_dengan": row.data.get("D") if row else None})
    return {"diunggah": out, "gagal": errors}


class PhotoPatch(BaseModel):
    public_url: str | None = None
    row_id: int | None = None
    set_main: bool = False


@router.patch("/photos/{pid}")
def patch_photo(bid: int, pid: int, body: PhotoPatch, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    s = ctx.session
    p = s.get(Photo, pid)
    if not p or p.batch_id != b.id or p.company_id != ctx.company.id:
        raise HTTPException(404, "Foto tidak ditemukan")
    if body.public_url is not None:
        u = body.public_url.strip()
        if u and not (PNG_RE.match(u) or re.match(r"^https?://(drive|docs)\.google\.com/\S+$", u, re.I)):
            raise HTTPException(400, "Link harus berakhiran .png (imgur) atau link Google Drive 'siapa saja dengan link'")
        p.public_url = u
    if body.row_id is not None:
        r = s.get(ProductRow, body.row_id)
        if body.row_id and (not r or r.batch_id != b.id):
            raise HTTPException(404, "Baris tidak ditemukan")
        p.row_id = body.row_id or None
    s.add(p)
    s.commit()
    if body.set_main and p.row_id and b.status in EDITABLE:   # jadikan foto utama produk
        r = s.get(ProductRow, p.row_id)
        d = dict(r.data)
        d["E"] = p.filename
        r.data = d
        s.add(r)
        s.commit()
    return photo_dict(p)


@router.delete("/photos/{pid}")
def delete_photo(bid: int, pid: int, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    s = ctx.session
    p = s.get(Photo, pid)
    if not p or p.batch_id != b.id or p.company_id != ctx.company.id:
        raise HTTPException(404, "Foto tidak ditemukan")
    try:
        import os
        os.remove(p.path)
    except OSError:
        pass
    s.delete(p)
    s.commit()
    return {"ok": True}


@router.get("/photos/{pid}/file")
def photo_file(bid: int, pid: int, ctx: Ctx = Depends(any_member)):
    b = get_batch(ctx, bid)
    p = ctx.session.get(Photo, pid)
    if not p or p.batch_id != b.id or p.company_id != ctx.company.id:
        raise HTTPException(404, "Foto tidak ditemukan")
    return FileResponse(p.path, media_type="image/png", filename=p.filename)


@router.get("/photos.zip")
def photos_zip(bid: int, ctx: Ctx = Depends(any_member)):
    b = get_batch(ctx, bid)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in photos_of(ctx, b):
            try:
                z.write(p.path, p.filename)
            except OSError:
                continue
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="foto_batch{b.id}.zip"'})


@router.post("/banner")
def banner(bid: int, body: BannerIn, ctx: Ctx = Depends(need("admin", "operator"))):
    b = get_batch(ctx, bid)
    if b.status not in EDITABLE:
        raise HTTPException(409, "Batch tidak bisa diubah pada status ini")
    if not body.title.strip():
        raise HTTPException(400, "Nama layanan wajib")
    data = ph.make_banner(body.title.strip(), body.points, body.company or ctx.company.name)
    path = pdir(ctx, b) / f"{uuid.uuid4().hex}.png"
    path.write_bytes(data)
    name = f"banner-{slug(body.title)[:60] or 'jasa'}.png"
    p = Photo(company_id=ctx.company.id, batch_id=b.id, row_id=body.row_id, filename=name, path=str(path),
              width=ph.TARGET, height=ph.TARGET, size=len(data), kind="banner")
    ctx.session.add(p)
    ctx.session.commit()
    ctx.session.refresh(p)
    return photo_dict(p)

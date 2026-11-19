import io
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlmodel import select

from ..deps import Ctx, any_member, audit, need
from ..models import ProductRow, TemplateSchema
from ..services.form_io import blank_form
from ..services.seed import import_template_bytes

router = APIRouter(prefix="/api/companies/{company_id}/templates", tags=["template"])


def schema_dict(t: TemplateSchema, full: bool = False) -> dict:
    d = {"id": t.id, "slug": t.slug, "category_name": t.category_name, "jenis": t.jenis, "filename": t.filename,
         "category_uuid": t.category_uuid, "category_id": t.category_id, "category_path": t.category_path,
         "kbki": t.kbki, "n_kolom": len(t.columns)}
    if full:
        d["columns"] = t.columns
        d["negara"] = t.negara
    return d


@router.get("")
def list_templates(full: bool = False, ctx: Ctx = Depends(any_member)):
    rows = ctx.session.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id)
                            .order_by(TemplateSchema.category_name)).all()
    return [schema_dict(t, full) for t in rows]


@router.get("/blank-form")
def form_kosong(ctx: Ctx = Depends(any_member)):
    rows = ctx.session.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id)).all()
    data = blank_form(sorted(rows, key=lambda t: t.category_name), ctx.company.name)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="Form_Data_Produk_kosong.xlsx"'})


@router.get("/{tid}")
def get_template(tid: int, ctx: Ctx = Depends(any_member)):
    t = ctx.session.get(TemplateSchema, tid)
    if not t or t.company_id != ctx.company.id:
        raise HTTPException(404, "Template tidak ditemukan")
    return schema_dict(t, True)


@router.post("")
async def upload_templates(files: list[UploadFile] = File(...), ctx: Ctx = Depends(need("admin"))):
    """Unggah satu/banyak template .xlsx atau sebuah .zip. Template milik perusahaan lain atau kategori 'Tidak Bisa' ditolak."""
    s = ctx.session
    items = []
    for f in files:
        raw = await f.read()
        if f.filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    for n in z.namelist():
                        if n.lower().endswith(".xlsx") and not n.startswith("__MACOSX"):
                            items.append((n.split("/")[-1], z.read(n)))
            except zipfile.BadZipFile:
                items.append((f.filename, b""))
        else:
            items.append((f.filename, raw))
    ok, rejected = [], []
    for name, raw in items:
        try:
            t = import_template_bytes(s, ctx.company, raw, name)
            ok.append(schema_dict(t))
        except ValueError as e:
            rejected.append({"file": name, "alasan": str(e)})
    audit(s, ctx.user, ctx.company.id, "template.unggah", f"{len(ok)} diterima, {len(rejected)} ditolak")
    return {"diterima": ok, "ditolak": rejected}


@router.delete("/{tid}")
def delete_template(tid: int, ctx: Ctx = Depends(need("admin"))):
    s = ctx.session
    t = s.get(TemplateSchema, tid)
    if not t or t.company_id != ctx.company.id:
        raise HTTPException(404, "Template tidak ditemukan")
    if s.exec(select(ProductRow).where(ProductRow.schema_id == tid).limit(1)).first():
        raise HTTPException(409, "Template masih dipakai oleh produk di batch")
    s.delete(t)
    s.commit()
    audit(s, ctx.user, ctx.company.id, "template.hapus", t.category_name)
    return {"ok": True}

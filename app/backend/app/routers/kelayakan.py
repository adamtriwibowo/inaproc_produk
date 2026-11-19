import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlmodel import select

from ..deps import Ctx, any_member
from ..models import Category, TemplateSchema
from ..services import kelayakan

router = APIRouter(prefix="/api/companies/{company_id}/kelayakan", tags=["kelayakan"])


@router.get("/tree")
def tree(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    ex = kelayakan.existing_counts(s, ctx.company.id)
    t = kelayakan.build_tree(s, ctx.company.id, ex)
    tpl = {x.category_id for x in s.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id)) if x.category_id}
    for n1 in t["tree"]:
        for n2 in n1["children"]:
            for c in n2["children"]:
                c["punya_template"] = c["id"] in tpl
    return t


@router.get("/category/{cat_id}")
def category(cat_id: int, ctx: Ctx = Depends(any_member)):
    s = ctx.session
    cat = s.get(Category, cat_id)
    if not cat:
        raise HTTPException(404, "Kategori tidak ditemukan")
    d = kelayakan.category_detail(s, ctx.company.id, cat)
    tpl = s.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id, TemplateSchema.category_id == cat.id)).first()
    d["template_id"] = tpl.id if tpl else None
    d["punya_template"] = bool(tpl)
    d["flags"] = kelayakan.flag_for(cat)
    d["catatan"] = (None if tpl or not d["ok"] else
                    "Kategori ini belum punya template. Unduh di INAPROC: Produk › Atur Produk Sekaligus › Unduh Template "
                    "(maksimal 100 kategori per unduhan, dikirim lewat email), lalu unggah di menu Template.")
    return d


@router.get("/rekomendasi")
def rekomendasi(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    tpl_ids = {x.category_id for x in s.exec(select(TemplateSchema).where(TemplateSchema.company_id == ctx.company.id))}
    tpl_l3 = {c.l3 for c in kelayakan.all_categories(s) if c.id in tpl_ids}
    return kelayakan.rekomendasi(s, ctx.company.id, tpl_l3)


@router.get("/peringatan")
def peringatan(ctx: Ctx = Depends(any_member)):
    return kelayakan.existing_warnings(ctx.session, ctx.company.id)


@router.get("/export.xlsx")
def export_xlsx(ctx: Ctx = Depends(any_member)):
    s = ctx.session
    kset = kelayakan.kbli_set(s, ctx.company.id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Semua Kategori"
    ws.append(["Kategori Utama", "Subkategori", "Kategori Produk", "Jenis", "Status", "KBLI perusahaan cocok"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E40AF")
    for c in sorted(kelayakan.all_categories(s), key=lambda x: (x.l1.lower(), x.l2.lower(), x.l3.lower())):
        m = kelayakan.matched(c, kset)
        ws.append([c.l1, c.l2, c.l3, c.product_type, "Bisa" if m else "Tidak Bisa", ", ".join(m)])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col, w in zip("ABCDEF", (32, 36, 40, 8, 12, 30)):
        ws.column_dimensions[col].width = w
    w2 = wb.create_sheet("Rekomendasi")
    w2.append(["Prioritas", "Kategori Utama", "Subkategori", "Kategori Produk", "Catatan"])
    for r in kelayakan.rekomendasi(s, ctx.company.id, set()):
        w2.append([r["prioritas"], r["l1"], r["l2"], r["l3"], "; ".join(r["flags"])])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="rekap_kelayakan_kategori.xlsx"'})

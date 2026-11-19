"""Membaca skema template resmi INAPROC (.xlsx): ID di B1-B3, kolom baris 4-6, data validation, sheet pendukung."""
import io
import json
import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .. import config

REQ_MAP = {
    "(wajib)": "wajib",
    "(opsional)": "opsional",
    "(kosongkan)": "kosongkan",
    "(wajib jika aktif)": "wajib_jika_aktif",
    "(terisi otomatis)": "otomatis",
}


class TemplateError(ValueError):
    pass


def _cat_names() -> dict:
    p = config.TEMPLATES_SRC / "cat_names.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def slug_from_filename(name: str) -> str:
    m = re.search(r"Sekaligus_-_(.+?)_-_Format", name)
    return m.group(1) if m else Path(name).stem


def jenis_from_filename(name: str, cols: list) -> str:
    low = name.lower()
    if "_-_jasa_-_" in low:
        return "Jasa"
    if "_-_barang_-_" in low:
        return "Barang"
    # cadangan: kolom berat berlabel (Kosongkan) -> Jasa
    for c in cols:
        if c["label"] and c["label"].startswith("Berat Produk"):
            return "Jasa" if c["req"] == "kosongkan" else "Barang"
    return "Barang"


def _list_from_range(wb, formula: str):
    m = re.match(r"^'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)$", formula)
    if not m or m.group(1) not in wb.sheetnames:
        return None
    ws = wb[m.group(1)]
    col = m.group(2)
    r1, r2 = int(m.group(3)), int(m.group(5))
    out = []
    for r in range(r1, r2 + 1):
        v = ws[f"{col}{r}"].value
        if v not in (None, ""):
            out.append(str(v))
    return out


def scan_workbook(data: bytes, filename: str) -> dict:
    """Mengembalikan dict skema. Melempar TemplateError bila bukan template INAPROC yang valid."""
    try:
        wb = load_workbook(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001
        raise TemplateError(f"File bukan .xlsx yang valid: {e}")
    ws = wb.worksheets[0]
    if str(ws["A1"].value or "").strip() != "Institution ID" or str(ws["A2"].value or "").strip() != "Category ID":
        raise TemplateError("Bukan template INAPROC (A1 harus 'Institution ID' dan A2 'Category ID').")
    inst, cat, tpl = (str(ws[f"B{i}"].value or "").strip() for i in (1, 2, 3))
    if not inst or not cat:
        raise TemplateError("Institution ID / Category ID di template kosong.")

    # data validation per kolom
    dv_by_col = {}
    for dv in ws.data_validations.dataValidation:
        f1 = str(dv.formula1 or "")
        if dv.type != "list" or not f1:
            continue
        if f1.startswith('"'):
            opts = [x for x in f1.strip('"').split(",")]
        else:
            opts = _list_from_range(wb, f1)
        if opts is None:
            continue
        for rng in str(dv.sqref).split():
            col = re.match(r"[A-Z]+", rng).group(0)
            dv_by_col[col] = opts

    cols = []
    group = None
    for c in range(1, ws.max_column + 1):
        g = ws.cell(4, c).value
        if g:
            group = str(g)
        label = ws.cell(5, c).value
        req_raw = str(ws.cell(6, c).value or "").strip().lower()
        letter = get_column_letter(c)
        hint = ws.cell(7, c).value
        if c >= 3 and not label and not req_raw and c > 3:
            continue
        cols.append({
            "letter": letter, "idx": c, "group": group,
            "label": str(label) if label else (str(g) if g else letter),
            "req": REQ_MAP.get(req_raw, "opsional" if c > 2 else "sistem"),
            "hint": str(hint) if hint else "",
            "options": dv_by_col.get(letter),
        })
    # kolom A (Status) & B (Pesan Error) diisi sistem
    for c in cols[:2]:
        c["req"] = "sistem"

    def sheet_rows(name, n):
        if name not in wb.sheetnames:
            return []
        return [[x.value for x in r[:n]] for r in wb[name].iter_rows(min_row=2) if r[0].value not in (None, "")]

    kbki = [[str(a), str(b or "")] for a, b in sheet_rows("Daftar KBKI", 2)]
    negara = [str(a) for a, _ in sheet_rows("Daftar Negara Asal", 2)]
    ppnbm = sheet_rows("Daftar PPNBM", 3)
    for c in cols:
        if c["letter"] == "N" and ppnbm:
            c["options"] = [str(r[0]) for r in ppnbm]
        if c["letter"] == "O" and ppnbm:
            c["options"] = [str(r[2]) for r in ppnbm]
        if c["letter"] == "Q":
            c["options"] = [k[0] for k in kbki]
    jenis = jenis_from_filename(filename, cols)
    slug = slug_from_filename(filename)
    names = _cat_names()
    return {
        "slug": slug, "category_name": names.get(slug) or slug.replace("-", " ").title(),
        "institution_id": inst, "category_uuid": cat, "template_id": tpl,
        "jenis": jenis, "columns": cols, "kbki": kbki, "negara": negara,
    }


def col_by_label(columns: list, label: str):
    """Cari kolom menurut label (kolom atribut berbeda per kategori)."""
    low = label.lower()
    for c in columns:
        if (c["label"] or "").lower() == low:
            return c["letter"]
    return None

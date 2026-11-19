"""Isi template resmi (salin template asli -> delete_rows(7,3) -> tulis mulai baris 7) lalu zip tanpa folder."""
import io
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.utils import column_index_from_string

from .. import config
from .validator import PHOTO_COLS, empty, parse_int, resolve_photo

NUMERIC = {"X", "Z", "AB", "AC", "AD", "AE", "AF", "AG"}
CODE_COLS = {"Q", "V"}          # "KODE - Nama" -> "KODE"


class ExportError(ValueError):
    pass


def cell_value(col: str, v, photos: dict):
    if empty(v):
        return None
    if col in PHOTO_COLS:
        return resolve_photo(v, photos)
    if col in NUMERIC:
        n = parse_int(v)
        return n if n is not None else v
    if col in CODE_COLS:
        return str(v).split(" - ")[0].strip()
    if isinstance(v, str):
        return v.strip()
    return v


def fill_template(schema, rows: list, status: str, photos: dict | None = None) -> bytes:
    """rows: list dict data (kunci huruf kolom). Mengembalikan bytes .xlsx."""
    photos = photos or {}
    wb = load_workbook(schema.stored_path)
    ws = wb.worksheets[0]
    if str(ws["B1"].value or "").strip() != schema.institution_id:
        raise ExportError("Institution ID di template berubah.")
    ws.delete_rows(7, 3)  # hapus baris petunjuk & contoh (7-9)
    skip = {c["letter"] for c in schema.columns if c["req"] in ("kosongkan", "otomatis", "sistem")} | {"U", "A", "B"}
    for i, data in enumerate(rows):
        r = 7 + i
        d = dict(data)
        d["C"] = status
        for col, v in d.items():
            if col in skip:
                continue
            out = cell_value(col, v, photos)
            if out is not None:
                ws.cell(r, column_index_from_string(col), out)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def pack_zips(files: list, base: str, max_bytes: int = config.MAX_ZIP_BYTES) -> list:
    """files: [(nama, bytes)] -> [(nama_zip, bytes)] tanpa folder, tiap zip <= max_bytes."""
    groups, cur, size = [], [], 0
    for name, data in files:
        est = len(data)
        if est > max_bytes:
            raise ExportError(f"File {name} lebih dari 50 MB.")
        if cur and size + est > max_bytes * 0.95:   # margin untuk overhead zip
            groups.append(cur)
            cur, size = [], 0
        cur.append((name, data))
        size += est
    if cur:
        groups.append(cur)
    out = []
    for gi, g in enumerate(groups, 1):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in g:
                z.writestr(name, data)
        zname = f"{base}.zip" if len(groups) == 1 else f"{base}_bagian{gi}.zip"
        if buf.tell() > max_bytes:
            raise ExportError("Ukuran zip melebihi 50 MB; pecah batch.")
        out.append((zname, buf.getvalue()))
    return out


def build_report(batch, company, items: list, warnings: list) -> bytes:
    """items: [(kategori, nama, harga, kbki, status_baris)]. Laporan terpisah dari zip."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Produk"
    ws.append(["Perusahaan", company.name, "Institution ID", company.institution_id])
    ws.append(["Batch", batch.name, "Status ekspor", "Tayang" if not batch.is_test else "Uji coba (Tidak Tayang)"])
    ws.append([])
    ws.append(["Kategori", "Nama Produk", "Harga", "Kode KBKI"])
    for it in items:
        ws.append(list(it))
    w2 = wb.create_sheet("Peringatan")
    w2.append(["Baris/Produk", "Peringatan"])
    for a, b in warnings:
        w2.append([a, b])
    w3 = wb.create_sheet("Tindak lanjut manual")
    w3.append(["Hal yang tidak tercakup unggah massal — lakukan manual di INAPROC setelah produk masuk"])
    for t in ("Varian produk", "Harga grosir", "Layanan tambahan", "Merek", "TKDN", "SNI"):
        w3.append([t])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

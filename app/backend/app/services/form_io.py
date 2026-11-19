"""Impor / ekspor 'Form_Data_Produk_*.xlsx' (format scripts/form.py)."""
import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .template_scan import col_by_label

BARANG_HEAD = [
    "No", "Kategori *", "Nama Produk *", "Tipe / Model", "Spesifikasi Produk", "Deskripsi Produk", "Garansi",
    "Harga Satuan (Rp, nett) *", "PPN *", "Jumlah Stok *", "Satuan *", "Minimum Pembelian *", "Berat (gram) *",
    "Panjang (cm)", "Lebar (cm)", "Tinggi (cm)", "Lokasi Produksi *", "Tenaga Kerja *", "Bahan Baku *",
    "Negara Asal *", "Pre Order?", "Lama Pre Order (hari)", "Foto Utama (link .png / nama file) *", "Foto 2",
    "Foto 3", "Foto 4", "Foto 5", "URL Video (YouTube)", "Kode KBKI", "Catatan untuk saya"]
JASA_HEAD = [
    "No", "Nama Layanan *", "Deskripsi Layanan", "Rincian Layanan Servis", "Garansi Layanan", "Harga (Rp, nett) *",
    "PPN *", "Kuota / Stok *", "Satuan *", "Minimum Pembelian *", "Lokasi Produksi *", "Tenaga Kerja *",
    "Bahan Baku *", "Negara Asal *", "Ada Komponen Biaya Personil?", "Komponen Biaya Lainnya", "Pre Order?",
    "Lama Pre Order (hari)", "Foto Utama (link .png / nama file) *", "Foto 2", "Foto 3", "Catatan untuk saya"]


def _code(v):
    return str(v).split(" - ")[0].strip() if v not in (None, "") else None


def _po(po, hari):
    on = str(po or "").strip().lower() in ("ya", "aktif", "yes")
    return ("Aktif", hari) if on else ("Tidak Aktif", None)


def import_form(data: bytes, schemas: list):
    """Mengembalikan (rows, issues); rows = [(schema, data_dict)]."""
    wb = load_workbook(io.BytesIO(data), data_only=True)
    by_name = {s.category_name.lower(): s for s in schemas}
    rows, issues = [], []

    if "Barang" in wb.sheetnames:
        for r in wb["Barang"].iter_rows(min_row=2, values_only=True):
            r = list(r) + [None] * (30 - len(r))
            if not r[2] or str(r[0]).strip().upper() == "CONTOH":
                continue
            sc = by_name.get(str(r[1] or "").strip().lower())
            if not sc or sc.jenis != "Barang":
                issues.append(f"'{r[2]}': kategori '{r[1]}' belum punya template di perusahaan ini — dilewati")
                continue
            (_no, _kat, nama, tipe, spek, desk, garansi, harga, ppn, stok, sat, minb, berat, p, l, t, pd, tk, bb, neg,
             po, poh, f1, f2, f3, f4, f5, vid, kbki, _cat) = r[:30]
            po_v, po_h = _po(po, poh)
            d = {"D": str(nama).strip(), "K": desk, "L": ppn or "12%", "M": "Tidak Aktif", "Q": _code(kbki),
                 "R": pd, "S": tk, "T": bb, "V": _code(neg), "W": "Tidak Aktif", "X": stok, "Y": sat,
                 "Z": minb or 1, "AA": po_v, "AB": po_h, "AC": harga, "AD": berat, "AE": p, "AF": l, "AG": t,
                 "AH": "STANDARD", "J": vid}
            for k, f in zip("EFGHI", (f1, f2, f3, f4, f5)):
                d[k] = f
            for lab, v in (("Tipe", tipe), ("Spesifikasi Produk", spek), ("Garansi", garansi)):
                k = col_by_label(sc.columns, lab)
                if k:
                    d[k] = v
            rows.append((sc, {k: v for k, v in d.items() if v not in (None, "")}))

    for name in wb.sheetnames:
        if name in ("Petunjuk", "Barang", "Daftar Pilihan"):
            continue
        sc = by_name.get(name.lower())
        if not sc or sc.jenis != "Jasa":
            continue
        for r in wb[name].iter_rows(min_row=2, values_only=True):
            r = list(r) + [None] * (22 - len(r))
            if not r[1] or str(r[0]).strip().upper() == "CONTOH":
                continue
            (_no, nama, desk, rincian, garansi, harga, ppn, stok, sat, minb, pd, tk, bb, neg, personil, biaya_lain,
             po, poh, f1, f2, f3, _cat) = r[:22]
            po_v, po_h = _po(po, poh)
            d = {"D": str(nama).strip(), "K": desk, "L": ppn or "12%", "M": "Tidak Aktif", "R": pd, "S": tk, "T": bb,
                 "V": _code(neg), "W": "Tidak Aktif", "X": stok, "Y": sat, "Z": minb or 1, "AA": po_v, "AB": po_h,
                 "AC": harga, "E": f1, "F": f2, "G": f3}
            for lab, v in (("Rincian Layanan Servis", rincian), ("Garansi Layanan", garansi),
                           ("Komponen Biaya Personil", personil), ("Komponen Biaya Lainnya (Apabila ada)", biaya_lain)):
                k = col_by_label(sc.columns, lab)
                if k:
                    d[k] = v
            rows.append((sc, {k: v for k, v in d.items() if v not in (None, "")}))
    return rows, issues


def blank_form(schemas: list, company_name: str) -> bytes:
    """Form kosong dari skema template perusahaan."""
    wb = Workbook()
    pet = wb.active
    pet.title = "Petunjuk"
    pet["A1"] = f"Form Data Produk — {company_name}"
    pet["A1"].font = Font(bold=True, size=13)
    for i, t in enumerate([
        "", "Cara mengisi:",
        '1. Barang di sheet "Barang", jasa di sheet nama kategorinya.',
        "2. Kolom bertanda * wajib. Harga bilangan bulat nett tanpa pemisah (85000).",
        "3. Foto: link publik .png atau nama file yang akan diunggah di aplikasi.",
        "4. Impor file ini lewat menu Batch › Impor Form.",
        "Tidak tersedia di unggah massal: varian, harga grosir, layanan tambahan, merek, TKDN, SNI."], 2):
        pet[f"A{i}"] = t
    pet.column_dimensions["A"].width = 100

    barang = [s for s in schemas if s.jenis == "Barang"]
    jasa = [s for s in schemas if s.jenis == "Jasa"]
    lists = wb.create_sheet("Daftar Pilihan")
    ref = barang[0] if barang else (schemas[0] if schemas else None)

    def opts(sc, letter):
        for c in sc.columns:
            if c["letter"] == letter:
                return c.get("options") or []
        return []

    cols = {
        "Kategori": [s.category_name for s in barang], "PPN": opts(ref, "L") if ref else [],
        "Satuan": opts(ref, "Y") if ref else [], "PDN_Produksi": opts(ref, "R") if ref else [],
        "PDN_TenagaKerja": opts(ref, "S") if ref else [], "PDN_BahanBaku": opts(ref, "T") if ref else [],
        "YaTidak": ["Ya", "Tidak"], "Negara": ref.negara if ref else [],
        "KBKI": [f"{k[0]} - {k[1]} [{s.category_name}]" for s in barang for k in s.kbki],
    }
    pos = {}
    for j, (h, vals) in enumerate(cols.items(), 1):
        lists.cell(1, j, h).font = Font(bold=True)
        for i, v in enumerate(vals, 2):
            lists.cell(2 + i - 2, j, v)
        pos[h] = (get_column_letter(j), max(len(vals) + 1, 2))

    fill = PatternFill("solid", fgColor="FFF2CC")

    def sheet(title, head, dvmap):
        ws = wb.create_sheet(title)
        for j, h in enumerate(head, 1):
            c = ws.cell(1, j, h)
            c.font = Font(bold=True)
            if h.endswith("*"):
                c.fill = fill
            c.alignment = Alignment(wrap_text=True, vertical="center")
            ws.column_dimensions[get_column_letter(j)].width = 22
        ws.freeze_panes = "C2"
        for j, key in dvmap.items():
            L, n = pos[key]
            dv = DataValidation(type="list", formula1=f"='Daftar Pilihan'!${L}$2:${L}${n}", allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{get_column_letter(j)}2:{get_column_letter(j)}200")
        return ws

    if barang:
        sheet("Barang", BARANG_HEAD, {2: "Kategori", 9: "PPN", 11: "Satuan", 17: "PDN_Produksi", 18: "PDN_TenagaKerja",
                                       19: "PDN_BahanBaku", 20: "Negara", 21: "YaTidak", 29: "KBKI"})
    for s in jasa:
        sheet(s.category_name[:31], JASA_HEAD, {7: "PPN", 9: "Satuan", 11: "PDN_Produksi", 12: "PDN_TenagaKerja",
                                               13: "PDN_BahanBaku", 14: "Negara", 15: "YaTidak", 17: "YaTidak"})
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

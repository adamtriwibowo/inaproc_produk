"""Validasi per sel berdasarkan aturan di knowledge/PENGETAHUAN_INAPROC.md dan skema template."""
import re
from dataclasses import dataclass, field

PNG_RE = re.compile(r"^https?://\S+\.png(\?\S*)?$", re.I)
DRIVE_RE = re.compile(r"^https?://(drive|docs)\.google\.com/\S+$", re.I)
URL_RE = re.compile(r"^https?://\S+$", re.I)
INT_RE = re.compile(r"^\d+$")

PHOTO_COLS = ["E", "F", "G", "H", "I"]


def empty(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def parse_int(v):
    """Bilangan bulat > 0 tanpa pemisah. Mengembalikan int atau None bila tidak valid."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    s = str(v).strip()
    return int(s) if INT_RE.match(s) else None


def is_url_png(v) -> bool:
    return bool(PNG_RE.match(str(v).strip()))


def norm_name(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


@dataclass
class Ctx:
    photos: dict = field(default_factory=dict)         # nama file (lower) -> Photo
    name_counts: dict = field(default_factory=dict)    # nama normal -> jumlah di batch
    existing_names: set = field(default_factory=set)   # nama normal pada batch lain yang sudah diekspor/diunggah


def resolve_photo(value, photos: dict):
    """Nilai kolom foto -> URL publik (atau None bila belum punya)."""
    if empty(value):
        return None
    v = str(value).strip()
    if URL_RE.match(v):
        return v
    p = photos.get(v.lower())
    if p and p.public_url:
        return p.public_url
    return None


def validate_row(schema, data: dict, ctx: Ctx) -> list:
    issues = []
    cols = {c["letter"]: c for c in schema.columns}

    def err(col, msg, level="error"):
        issues.append({"col": col, "level": level, "msg": msg})

    def val(k):
        return data.get(k)

    def has(k):
        return k in cols and not empty(val(k))

    def choice(k, label):
        c = cols.get(k)
        if not c or not has(k):
            return
        opts = c.get("options")
        if opts and str(val(k)).strip() not in opts and k not in ("Q", "N", "O"):
            err(k, f"{label}: nilai '{val(k)}' tidak ada di pilihan template")

    # nama
    nm = val("D")
    if empty(nm):
        err("D", "Nama produk wajib diisi")
    else:
        n = len(str(nm).strip())
        if not 10 <= n <= 100:
            err("D", f"Nama produk {n} karakter (harus 10–100)")
        key = norm_name(nm)
        if ctx.name_counts.get(key, 0) > 1:
            err("D", "Nama produk duplikat di dalam batch ini")
        if key in ctx.existing_names:
            err("D", "Nama produk sudah ada pada batch lain yang sudah diekspor/diunggah")

    # foto
    for k in PHOTO_COLS:
        if k not in cols or empty(val(k)):
            if k == "E":
                err("E", "Foto utama wajib (link publik .png atau file yang diunggah)")
            continue
        v = str(val(k)).strip()
        if URL_RE.match(v):
            if PNG_RE.match(v):
                continue
            if DRIVE_RE.match(v):
                err(k, "Link Google Drive: pastikan akses 'siapa saja dengan link' dan file berformat PNG", "warn")
                continue
            err(k, "Link foto harus berakhiran .png")
        else:
            ph = ctx.photos.get(v.lower())
            if not ph:
                err(k, "Foto harus berupa link publik .png atau nama file yang sudah diunggah")
            elif not ph.public_url:
                err(k, "Foto sudah diproses tetapi belum punya link publik (.png) — tempel link sebelum ekspor", "warn")
            elif not (PNG_RE.match(ph.public_url) or DRIVE_RE.match(ph.public_url)):
                err(k, "Link publik foto harus berakhiran .png")

    if has("J") and not URL_RE.match(str(val("J")).strip()):
        err("J", "URL video harus diawali http(s)://")
    if has("K") and not 10 <= len(str(val("K")).strip()) <= 100:
        err("K", "Deskripsi: template menyebut 10–100 karakter", "warn")

    # pajak & PPnBM
    if "L" in cols:
        if not has("L"):
            err("L", "PPN wajib diisi")
        else:
            choice("L", "PPN")
    if "M" in cols:
        if not has("M"):
            err("M", "Aktifkan PPnBM wajib diisi")
        else:
            choice("M", "PPnBM")
            if str(val("M")).strip() == "Aktif":
                for k, lab in (("N", "Jenis Produk"), ("O", "Kode"), ("P", "Status Pembayaran")):
                    if k in cols and not has(k):
                        err(k, f"PPnBM aktif: {lab} wajib diisi")
                choice("P", "Status pembayaran PPnBM")
                if has("O") and cols["O"].get("options") and str(val("O")).strip() not in cols["O"]["options"]:
                    err("O", "Kode PPnBM tidak ada di sheet Daftar PPNBM")

    # KBKI
    if "Q" in cols:
        if not has("Q"):
            err("Q", "Kode KBKI wajib diisi")
        else:
            code = str(val("Q")).split(" - ")[0].strip()
            valid = [k[0] for k in schema.kbki]
            if code not in valid:
                err("Q", f"KBKI {code} bukan milik kategori ini")

    # PDN
    for k, lab in (("R", "PDN produksi"), ("S", "PDN tenaga kerja"), ("T", "PDN bahan baku")):
        if k in cols:
            if not has(k):
                err(k, f"{lab} wajib diisi")
            else:
                choice(k, lab)
    if "V" in cols:
        if not has("V"):
            err("V", "Negara asal wajib diisi")
        else:
            code = str(val("V")).split(" - ")[0].strip()
            if schema.negara and code not in schema.negara:
                err("V", f"Kode negara '{code}' tidak ada di Daftar Negara Asal (ISO-3, mis. IDN)")
    if "W" in cols and has("W"):
        choice("W", "Kuantitas desimal")

    # stok, satuan, min beli
    for k, lab in (("X", "Jumlah stok"), ("Z", "Minimum pembelian")):
        if k in cols:
            if not has(k):
                err(k, f"{lab} wajib diisi")
            else:
                n = parse_int(val(k))
                if n is None or n <= 0:
                    err(k, f"{lab} harus bilangan bulat > 0")
    if "Y" in cols:
        if not has("Y"):
            err("Y", "Satuan wajib diisi")
        else:
            choice("Y", "Satuan")

    # pre order
    po = str(val("AA") or "").strip()
    if "AA" in cols and has("AA"):
        choice("AA", "Pre Order")
    if po == "Aktif":
        n = parse_int(val("AB"))
        if n is None or n <= 0:
            err("AB", "Pre Order aktif: jumlah hari wajib (bilangan bulat > 0)")

    # harga & pengiriman
    if "AC" in cols:
        if not has("AC"):
            err("AC", "Harga satuan wajib diisi")
        else:
            n = parse_int(val("AC"))
            if n is None or n <= 0:
                err("AC", "Harga harus bilangan bulat > 0, nett, tanpa pemisah (mis. 85000, bukan 85.000)")
    if schema.jenis == "Barang":
        if "AD" in cols:
            n = parse_int(val("AD")) if has("AD") else None
            if n is None or n <= 0:
                err("AD", "Berat (gram) wajib: bilangan bulat > 0")
        for k in ("AE", "AF", "AG"):
            if has(k):
                n = parse_int(val(k))
                if n is None or n <= 0:
                    err(k, "Dimensi harus bilangan bulat > 0 (cm)")
        if "AH" in cols:
            if not has("AH"):
                err("AH", "Opsi pengiriman wajib (STANDARD)")
            else:
                choice("AH", "Opsi pengiriman")

    # kolom atribut kategori & kolom lain: wajib / pilihan
    base = {"C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W",
            "X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI"}
    for k, c in cols.items():
        if k in base or c["req"] in ("sistem", "kosongkan", "otomatis"):
            continue
        if c["req"] == "wajib" and not has(k):
            err(k, f"{c['label']} wajib diisi")
        if has(k):
            choice(k, c["label"])
    return issues


def prepare_ctx(rows: list, photos: list, existing_names: set) -> Ctx:
    counts: dict = {}
    for r in rows:
        k = norm_name(r.data.get("D"))
        if k:
            counts[k] = counts.get(k, 0) + 1
    return Ctx(photos={p.filename.lower(): p for p in photos}, name_counts=counts, existing_names=existing_names)

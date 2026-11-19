"""Verifikasi nilai hasil AI terhadap sumber. AI DILARANG mengarang: nilai tanpa kutipan yang ada di sumber dibuang."""
import re

_WS = re.compile(r"\s+")
_TOK = re.compile(r"[a-z0-9]{2,}")


def norm(s) -> str:
    return _WS.sub(" ", str(s or "").lower()).strip()


def verify_text(nilai, kutipan, source_text: str | None):
    """Mengembalikan (nilai_bersih | None, verified: bool). source_text=None -> sumber tidak bisa dicek otomatis (PDF/gambar)."""
    if nilai is None or str(nilai).strip() == "":
        return None, True
    if not kutipan or not str(kutipan).strip():
        return None, True                            # tanpa kutipan = tanpa sumber -> kosongkan
    kq = norm(kutipan)
    if source_text is not None and kq not in norm(source_text):
        return None, True                            # kutipan tidak ada di sumber -> dibuang
    toks = _TOK.findall(norm(nilai))
    if toks:
        kt = set(_TOK.findall(kq))
        if sum(1 for t in toks if t in kt) / len(toks) < 0.6:
            return None, True                        # nilai tidak didukung kutipan
    return str(nilai).strip(), source_text is not None


_NUM = re.compile(r"\d[\d.,]*")


def parse_amount(s) -> int | None:
    """'Rp 85.000' / '85,000' / '1.250.000,50' -> int (rupiah, dibulatkan)."""
    m = _NUM.search(str(s or ""))
    if not m:
        return None
    t = m.group(0).rstrip(".,")
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        t = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        parts = t.split(sep)
        # 1.250 / 85,000 -> pemisah ribuan; 12,5 -> desimal
        t = "".join(parts) if len(parts[-1]) == 3 and len(parts) >= 2 else ".".join(parts)
    try:
        v = float(t)
    except ValueError:
        return None
    return int(round(v)) if v > 0 else None


_UNIT = re.compile(r"(\d[\d.,]*)\s*(kg|kilogram|gram|gr|g|mg|cm|mm|m|meter)?\b", re.I)


def parse_measure(s, kind: str) -> int | None:
    """kind='berat' -> gram; kind='panjang' -> cm. Mengubah satuan; satuan kosong dianggap gram/cm."""
    m = _UNIT.search(str(s or ""))
    if not m:
        return None
    raw, unit = m.group(1), (m.group(2) or "").lower()
    t = raw.replace(",", ".") if raw.count(",") == 1 and "." not in raw else raw.replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return None
    if kind == "berat":
        v *= {"kg": 1000, "kilogram": 1000, "mg": 0.001}.get(unit, 1)
    else:
        v *= {"mm": 0.1, "m": 100, "meter": 100}.get(unit, 1)
    return int(round(v)) if v >= 1 else None


def digits_in(quote: str, nilai) -> bool:
    """Angka pada nilai harus muncul pada kutipan (mencegah angka karangan)."""
    d = re.sub(r"\D", "", str(nilai or ""))
    return bool(d) and d in re.sub(r"\D", "", str(quote or ""))

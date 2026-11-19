"""Nilai default pintar, preset PDN, dan pemilihan KBKI otomatis (port dari scripts/convert.py)."""

PDN = {
    "Lokal": {
        "R": "Diproduksi di seluruh Indonesia",
        "S": "Dibuat oleh seluruh tenaga kerja Indonesia di dalam negeri",
        "T": "Seluruh bahan baku dalam negeri",
        "V": "IDN",
    },
    "Impor": {
        "R": "Tidak ada yang diproduksi di Indonesia",
        "S": "Tidak ada tenaga kerja Indonesia",
        "T": "Tidak ada bahan baku dalam negeri",
    },
}

KBKI_KEYWORDS = {
    "cakram": "Rem cakram", "kampas": "Rem cakram", "tromol": "Tromol rem", "sepatu": "Sepatu rem", "servo": "Rem servo",
    "tubeless": "Tubeless", "truk": "truk", "pelek": "Pelek", "velg": "Pelek", "dop": "Penutup pelek",
    "busi": "Busi", "kopling": "Kopling", "knalpot": "Knalpot", "fan belt": "Fan belt", "mounting": "Engine mounting",
    "klakson": "Klakson", "koil": "koil", "piston": "Piston", "filter": "filter",
}


def pick_kbki(kbki_opts: list, name: str):
    """Mengembalikan (kode, perlu_dicek). Satu kode -> langsung; lebih dari satu -> tebak dari nama."""
    if not kbki_opts:
        return None, False
    if len(kbki_opts) == 1:
        return kbki_opts[0][0], False
    t = (name or "").lower()
    for k, want in KBKI_KEYWORDS.items():
        if k in t:
            for code, desc in kbki_opts:
                if want.lower() in (desc or "").lower():
                    return code, True
    return kbki_opts[0][0], True


def apply_defaults(schema, data: dict, preset: str = "Lokal", force: bool = False) -> dict:
    """Isi default hanya pada sel kosong. Mengembalikan (data baru, kbki_guess)."""
    d = dict(data)
    letters = {c["letter"]: c for c in schema.columns}

    def put(k, v):
        if k in letters and letters[k]["req"] != "kosongkan" and (force or d.get(k) in (None, "")):
            d[k] = v

    put("L", "12%")
    put("M", "Tidak Aktif")
    put("W", "Tidak Aktif")
    put("Z", 1)
    put("AA", "Tidak Aktif")
    if schema.jenis == "Barang":
        put("AH", "STANDARD")
    for k, v in PDN.get(preset, PDN["Lokal"]).items():
        put(k, v)
    guess = False
    if d.get("Q") in (None, "") and "Q" in letters:
        code, guess = pick_kbki(schema.kbki, d.get("D", ""))
        if code:
            d["Q"] = code
    return d, guess

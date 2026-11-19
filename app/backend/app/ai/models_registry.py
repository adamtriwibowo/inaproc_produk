"""Validasi slot model terhadap daftar model OpenRouter (kemampuan nyata, bukan tebakan) + harga."""
import time

from . import ai_client

# Kebutuhan tiap slot
SLOT_NEEDS = {
    "model_ekstraksi": {"structured"},
    "model_sulit": {"structured", "tools"},
    "model_eskalasi": {"structured"},
    "model_vision": {"structured", "image_in"},
    "model_gambar": {"image_out"},
}
NEED_LABEL = {"structured": "structured outputs", "tools": "tools", "image_in": "input gambar", "image_out": "output gambar"}
_cache: dict = {"t": 0.0, "key": None, "text": [], "image": []}
TTL = 600


def _caps(m: dict) -> set:
    sp = set(m.get("supported_parameters") or [])
    arch = m.get("architecture") or {}
    ins, outs = set(arch.get("input_modalities") or []), set(arch.get("output_modalities") or [])
    caps = set()
    if sp & {"structured_outputs", "response_format"}:
        caps.add("structured")
    if "tools" in sp:
        caps.add("tools")
    if "image" in ins:
        caps.add("image_in")
    if "image" in outs:
        caps.add("image_out")
    return caps


def _price(m: dict) -> dict:
    p = m.get("pricing") or {}

    def per_m(v):
        try:
            return round(float(v) * 1_000_000, 4)
        except (TypeError, ValueError):
            return None
    return {"input_per_1m": per_m(p.get("prompt")), "output_per_1m": per_m(p.get("completion")),
            "per_image": p.get("image") if p.get("image") not in (None, "0") else None}


def load(api_key: str, force: bool = False) -> dict:
    """Muat daftar model (di-cache 10 menit per key)."""
    ck = hash(api_key)
    if not force and _cache["key"] == ck and time.time() - _cache["t"] < TTL:
        return _cache
    prov = ai_client.make_provider(api_key)
    text = prov.list_models()
    try:
        image = prov.list_image_models()
    except ai_client.AiError:
        image = []   # endpoint gambar bisa tidak tersedia; model gambar tetap dicek lewat /models
    _cache.update(t=time.time(), key=ck, text=text, image=image)
    return _cache


def find(reg: dict, slug: str):
    for m in reg["text"]:
        if m.get("id") == slug:
            return m, _caps(m)
    for m in reg["image"]:
        if m.get("id") == slug:
            return m, _caps(m) | {"image_out"}
    return None, set()


def validate_slot(reg: dict, slot: str, slug: str) -> str | None:
    """Mengembalikan pesan galat, atau None bila model cocok untuk slot."""
    if not slug:
        return None
    m, caps = find(reg, slug)
    if m is None:
        return f"Model '{slug}' tidak ditemukan di OpenRouter."
    missing = SLOT_NEEDS[slot] - caps
    if missing:
        return f"Model '{slug}' tidak mendukung {', '.join(NEED_LABEL[x] for x in sorted(missing))} yang dibutuhkan slot {slot}."
    return None


def listing(reg: dict, slot: str | None = None) -> list:
    """Daftar model ringkas (untuk dropdown pengaturan), disaring menurut kebutuhan slot."""
    need = SLOT_NEEDS.get(slot) if slot else None
    out = []
    seen = set()
    for m in [*reg["text"], *reg["image"]]:
        mid = m.get("id")
        if not mid or mid in seen:
            continue
        caps = _caps(m)
        if need and not need <= caps:
            continue
        seen.add(mid)
        out.append({"id": mid, "name": m.get("name") or mid, **_price(m), "caps": sorted(caps)})
    out.sort(key=lambda x: x["id"])
    return out


def price_of(reg: dict, slug: str) -> dict:
    m, _ = find(reg, slug)
    return _price(m) if m else {"input_per_1m": None, "output_per_1m": None, "per_image": None}

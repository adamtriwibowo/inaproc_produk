"""Estimasi biaya sebelum job dijalankan (token x harga model dari OpenRouter). Hanya perkiraan kasar."""
from sqlmodel import Session

from ..models import SourceDoc
from . import models_registry as reg, parsers, settings as aset

CHARS_PER_TOKEN = 3.5
OVERHEAD_IN = 900          # instruksi sistem per panggilan (sebagian ter-cache)
OUT_PER_ITEM = 150
CLASSIFY_IN_PER_ITEM = 450  # item + kandidat
CLASSIFY_OUT_PER_ITEM = 60


def estimate(s: Session, company_id: int, docs: list[SourceDoc], ocr: bool = False) -> dict:
    eff = aset.effective(s, company_id)
    calls = {"model_ekstraksi": [0, 0, 0], "model_sulit": [0, 0, 0], "model_vision": [0, 0, 0]}  # [panggilan, in, out]
    n_items = 0
    notes = []
    for d in docs:
        if d.kind in ("xlsx", "csv"):
            try:
                rows = parsers.parse_tabular(d.path, d.kind)
            except ValueError as e:
                notes.append(str(e))
                continue
            n_items += len(rows)
            for ch in parsers.chunk(rows):
                c = calls["model_ekstraksi"]
                c[0] += 1
                c[1] += int(sum(len(r["text"]) for r in ch) / CHARS_PER_TOKEN) + OVERHEAD_IN
                c[2] += OUT_PER_ITEM * len(ch)
        elif d.kind == "pdf":
            c = calls["model_sulit"]
            c[0] += 1
            c[1] += int(d.size / 4 / CHARS_PER_TOKEN * (3 if ocr else 1.5)) + OVERHEAD_IN     # kasar: ukuran file -> token
            c[2] += OUT_PER_ITEM * 30
            n_items += 30
            notes.append("Estimasi PDF sangat kasar" + (" (OCR lebih mahal)." if ocr else "."))
        else:
            c = calls["model_vision"]
            c[0] += 1
            c[1] += 1500 + OVERHEAD_IN
            c[2] += OUT_PER_ITEM * 2
            n_items += 1
    cl = calls["model_sulit"]
    for _ in range(0, n_items, 20):
        cl[0] += 1
    cl[1] += n_items * CLASSIFY_IN_PER_ITEM + OVERHEAD_IN
    cl[2] += n_items * CLASSIFY_OUT_PER_ITEM

    cost, priced = 0.0, True
    prices = {}
    if eff["api_key"]:
        try:
            r = reg.load(eff["api_key"])
            for slot, (n, tin, tout) in calls.items():
                if not n:
                    continue
                p = reg.price_of(r, eff["slots"][slot]["model"])
                prices[slot] = {"model": eff["slots"][slot]["model"], **p}
                if p["input_per_1m"] is None or p["output_per_1m"] is None:
                    priced = False
                else:
                    cost += tin / 1e6 * p["input_per_1m"] + tout / 1e6 * p["output_per_1m"]
        except Exception:  # noqa: BLE001
            priced = False
    else:
        priced = False
    q = aset.quota_status(s, company_id)
    return {
        "item_kira2": n_items, "panggilan": sum(v[0] for v in calls.values()),
        "token_masuk": sum(v[1] for v in calls.values()), "token_keluar": sum(v[2] for v in calls.values()),
        "biaya_usd": round(cost, 4) if priced else None, "harga_model": prices, "catatan": notes, "kuota": q,
        "melebihi_kuota": bool(priced and q["quota_usd"] is not None and q["spend_usd"] + cost > q["quota_usd"]),
    }

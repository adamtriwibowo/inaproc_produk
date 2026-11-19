"""Panggilan AI tingkat tinggi: kuota, pemilihan slot/model, structured output + validasi ulang, pencatatan biaya."""
from dataclasses import dataclass
from typing import Callable

from sqlmodel import Session

from ..models import AiUsage
from . import ai_client, settings as aset
from .ai_client import AiError, AiQuotaExceeded, AiResult


@dataclass
class CallCtx:
    company_id: int
    user_id: int | None = None
    batch_id: int | None = None
    job_id: int | None = None


def log_usage(s: Session, ctx: CallCtx, slot: str, res: AiResult | None, status: str = "ok", note: str = "", model: str = ""):
    s.add(AiUsage(
        company_id=ctx.company_id, user_id=ctx.user_id, batch_id=ctx.batch_id, job_id=ctx.job_id, slot=slot,
        model=(res.model if res else model), provider=(res.provider if res else ""),
        prompt_tokens=res.prompt_tokens if res else 0, completion_tokens=res.completion_tokens if res else 0,
        cost_usd=res.cost_usd if res else 0.0, duration_ms=res.duration_ms if res else 0, status=status, note=note[:300]))
    s.commit()


def ensure_ready(s: Session, ctx: CallCtx) -> dict:
    """Periksa key dan kuota. Bila habis, fitur AI berhenti dengan pesan jelas (fitur non-AI tetap jalan)."""
    eff = aset.effective(s, ctx.company_id)
    if not eff["api_key"]:
        raise AiError("API key OpenRouter belum diatur. Minta Admin mengisinya di Pengaturan AI.")
    q = aset.quota_status(s, ctx.company_id)
    if q["exhausted"]:
        raise AiQuotaExceeded(
            f"Kuota AI bulan ini habis (US$ {q['spend_usd']:.2f} dari US$ {q['quota_usd']:.2f}). "
            "Fitur AI berhenti; input manual dan pemrosesan foto lokal tetap berjalan.")
    return eff


def call_structured(s: Session, ctx: CallCtx, slot: str, messages: list, schema_name: str, schema: dict,
                    validate: Callable[[dict], object], plugins: list | None = None, escalate_slot: str | None = None):
    """Panggil model dengan output JSON ketat, validasi ulang di backend. Maks. 2x ulang:
    percobaan 1 = model slot, 2 = model cadangan slot, 3 = (opsional) slot eskalasi. Mengembalikan hasil validate()."""
    eff = ensure_ready(s, ctx)
    prov = ai_client.make_provider(eff["api_key"])
    sl = eff["slots"][slot]
    attempts: list[tuple[str, str, str]] = [(slot, sl["model"], sl["fallback"])]
    if sl["fallback"]:
        attempts.append((slot, sl["fallback"], ""))
    if escalate_slot and eff["slots"].get(escalate_slot, {}).get("model"):
        attempts.append((escalate_slot, eff["slots"][escalate_slot]["model"], ""))
    attempts = attempts[:3]
    last_err = "tidak diketahui"
    fmt = ai_client.json_schema_format(schema_name, schema)
    for slot_used, model, fb in attempts:
        # Cache prompt: pesan sistem diberi cache_control (instruksi + skema berulang tiap chunk)
        try:
            res = prov.chat(model=model, fallbacks=[fb] if fb else None, messages=messages, response_format=fmt,
                            plugins=plugins, no_retention=eff["no_data_retention"])
        except AiError as e:
            log_usage(s, ctx, slot_used, None, "error", str(e), model)
            last_err = str(e)
            if "401" in last_err or "402" in last_err:
                raise
            continue
        try:
            parsed = ai_client.parse_json(res.content)
            out = validate(parsed)
        except Exception as e:  # noqa: BLE001  JSON/skema tidak valid -> coba model cadangan
            log_usage(s, ctx, slot_used, res, "gagal_validasi", f"{type(e).__name__}: {e}")
            last_err = f"keluaran tidak valid ({type(e).__name__})"
            continue
        log_usage(s, ctx, slot_used, res, "ok")
        return out
    raise AiError(f"Gagal diproses AI: {last_err}")


def cached_system(text: str) -> dict:
    """Pesan sistem dengan penanda prompt caching (didukung Anthropic via OpenRouter; diabaikan model lain)."""
    return {"role": "system", "content": [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]}

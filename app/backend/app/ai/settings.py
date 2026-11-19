"""Pengaturan AI: key terenkripsi, slot model, kuota. Perusahaan menimpa pengaturan global bila diisi."""
import base64
import hashlib
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlmodel import Session, func, select

from .. import config
from ..models import AiSettings, AiUsage

SLOT_NAMES = ["model_ekstraksi", "model_sulit", "model_eskalasi", "model_vision", "model_gambar"]
DEFAULT_SLOTS = {
    "model_ekstraksi": {"model": "anthropic/claude-haiku-5.5", "fallback": "anthropic/claude-sonnet-5.5"},
    "model_sulit": {"model": "anthropic/claude-sonnet-5.5", "fallback": "anthropic/claude-opus-5.5"},
    "model_eskalasi": {"model": "anthropic/claude-opus-5.5", "fallback": ""},
    "model_vision": {"model": "anthropic/claude-haiku-5.5", "fallback": "anthropic/claude-sonnet-5.5"},
    "model_gambar": {"model": "meta/muse-image", "fallback": "bytedance-seed/seedream-5-0-flash"},
}
SLOT_LABEL = {
    "model_ekstraksi": "Ekstraksi (baris rapi, cek kualitas foto)",
    "model_sulit": "Kasus sulit (PDF/scan, klasifikasi, konten, chat)",
    "model_eskalasi": "Eskalasi (hanya bila gagal/meragukan)",
    "model_vision": "Vision (menilai/membaca foto)",
    "model_gambar": "Gambar (edit foto bila pipeline lokal gagal)",
}


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(("ai-key:" + config.SECRET_KEY).encode()).digest())
    return Fernet(key)


def encrypt(s: str) -> str:
    return _fernet().encrypt(s.encode()).decode() if s else ""


def decrypt(s: str) -> str:
    if not s:
        return ""
    try:
        return _fernet().decrypt(s.encode()).decode()
    except InvalidToken:
        return ""


def get_row(s: Session, company_id: int | None) -> AiSettings | None:
    q = select(AiSettings).where(AiSettings.company_id == company_id) if company_id is not None \
        else select(AiSettings).where(AiSettings.company_id == None)  # noqa: E711
    return s.exec(q).first()


def get_or_create(s: Session, company_id: int | None) -> AiSettings:
    row = get_row(s, company_id)
    if not row:
        row = AiSettings(company_id=company_id)
        s.add(row)
        s.commit()
        s.refresh(row)
    return row


def effective(s: Session, company_id: int) -> dict:
    """Pengaturan efektif: perusahaan menimpa global. Mengandung key terdekripsi: JANGAN dikirim ke frontend."""
    g, c = get_row(s, None), get_row(s, company_id)
    slots = {k: dict(v) for k, v in DEFAULT_SLOTS.items()}
    for src in (g, c):
        if src:
            for k, v in (src.slots or {}).items():
                if k in slots and isinstance(v, dict):
                    slots[k].update({a: b for a, b in v.items() if a in ("model", "fallback") and b is not None})
    key = decrypt(c.api_key_enc) if c and c.api_key_enc else (decrypt(g.api_key_enc) if g else "")
    return {
        "api_key": key,
        "key_source": "perusahaan" if c and c.api_key_enc else ("organisasi" if g and g.api_key_enc else "belum ada"),
        "slots": slots,
        "quota_usd": (c.quota_usd if c and c.quota_usd is not None else (g.quota_usd if g else None)),
        "name_pattern": (c.name_pattern if c else None) or (g.name_pattern if g else None) or AiSettings.model_fields["name_pattern"].default,
        "no_data_retention": bool((c and c.no_data_retention) or (g and g.no_data_retention)),
        "image_generate_enabled": bool(c and c.image_generate_enabled),
    }


def public_view(s: Session, company_id: int | None) -> dict:
    """Tampilan aman untuk frontend: tanpa key."""
    row = get_row(s, company_id)
    out = {
        "has_key": bool(row and row.api_key_enc),
        "slots": {k: dict(v) for k, v in DEFAULT_SLOTS.items()},
        "quota_usd": row.quota_usd if row else None,
        "name_pattern": row.name_pattern if row else AiSettings.model_fields["name_pattern"].default,
        "no_data_retention": bool(row and row.no_data_retention),
        "image_generate_enabled": bool(row and row.image_generate_enabled),
        "slot_defaults": DEFAULT_SLOTS, "slot_labels": SLOT_LABEL,
    }
    if row:
        for k, v in (row.slots or {}).items():
            if k in out["slots"]:
                out["slots"][k].update(v)
    return out


def month_start() -> datetime:
    n = datetime.now(timezone.utc)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_spend(s: Session, company_id: int) -> float:
    v = s.exec(select(func.coalesce(func.sum(AiUsage.cost_usd), 0.0)).where(
        AiUsage.company_id == company_id, AiUsage.ts >= month_start())).one()
    return float(v or 0.0)


def quota_status(s: Session, company_id: int) -> dict:
    eff = effective(s, company_id)
    spend, quota = month_spend(s, company_id), eff["quota_usd"]
    pct = (spend / quota * 100) if quota else None
    return {"spend_usd": round(spend, 4), "quota_usd": quota, "pct": round(pct, 1) if pct is not None else None,
            "warn": bool(pct is not None and pct >= 80), "exhausted": bool(quota is not None and spend >= quota)}

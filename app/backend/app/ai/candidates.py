"""Penyaringan kandidat kategori dengan KODE (bukan AI): hanya kategori 'Bisa' yang templatenya tersedia (maks. 30)."""
import re
from dataclasses import dataclass

from sqlmodel import Session, select

from ..models import Category, TemplateSchema
from ..services import kelayakan

MAX_CANDIDATES = 30
_STOP = {"dan", "atau", "untuk", "dengan", "yang", "dari", "pada", "set", "pcs", "unit", "new", "baru", "tipe", "type", "merk", "merek"}
_TOK = re.compile(r"[a-z0-9]{3,}")


def tokens(s: str) -> set:
    return {t for t in _TOK.findall((s or "").lower()) if t not in _STOP}


def _hit(a: set, b: set) -> int:
    n = 0
    for x in a:
        for y in b:
            if x == y or (len(x) >= 5 and len(y) >= 5 and (x.startswith(y[:5]) or y.startswith(x[:5]))):
                n += 1
                break
    return n


def score(item_tokens: set, cat: Category) -> int:
    return 3 * _hit(item_tokens, tokens(cat.l3)) + 2 * _hit(item_tokens, tokens(cat.l2)) + _hit(item_tokens, tokens(cat.l1))


@dataclass
class Pool:
    allowed: list          # Category yang boleh (Bisa + ada template), urut stabil
    schema_by_cat: dict    # category_id -> TemplateSchema
    kset: set


def build_pool(s: Session, company_id: int) -> Pool:
    kset = kelayakan.kbli_set(s, company_id)
    schemas = s.exec(select(TemplateSchema).where(TemplateSchema.company_id == company_id)).all()
    by_cat = {t.category_id: t for t in schemas if t.category_id}
    allowed = [c for c in kelayakan.all_categories(s) if c.id in by_cat and kelayakan.is_ok(c, kset)]
    allowed.sort(key=lambda c: (c.l1, c.l2, c.l3))
    return Pool(allowed=allowed, schema_by_cat=by_cat, kset=kset)


def candidates_for(pool: Pool, text: str, limit: int = MAX_CANDIDATES) -> list:
    """Urut menurut skor kata kunci. Bila kolam kecil (<= limit) semuanya dikirim; selain itu top-N."""
    it = tokens(text)
    ranked = sorted(pool.allowed, key=lambda c: (-score(it, c), c.l1, c.l2, c.l3))
    return ranked[:limit]


def locked_best(s: Session, pool: Pool, text: str):
    """Kategori paling cocok secara kata kunci di SELURUH pohon. Bila skornya lebih tinggi daripada kategori yang boleh dan
    kategori itu tidak boleh (Tidak Bisa / belum ada template), kembalikan informasinya untuk ditandai."""
    it = tokens(text)
    if not it:
        return None
    best, best_s = None, 0
    for c in kelayakan.all_categories(s):
        sc = score(it, c)
        if sc > best_s:
            best, best_s = c, sc
    if not best or best_s < 3:
        return None
    allowed_best = max((score(it, c) for c in pool.allowed), default=0)
    if best_s <= allowed_best or best.id in pool.schema_by_cat and kelayakan.is_ok(best, pool.kset):
        return None
    ok = kelayakan.is_ok(best, pool.kset)
    out = {"kategori": f"{best.l1} › {best.l2} › {best.l3}", "skor": best_s}
    if ok:
        out.update(status="Bisa", catatan="Kategori ini belum punya template. Unduh di INAPROC (Atur Produk Sekaligus › Unduh Template), lalu unggah di menu Template.")
    else:
        names = {}
        from ..models import KbliName
        for k in best.kbli_codes[:6]:
            code, ver = k.split("|")
            nm = s.exec(select(KbliName.name).where(KbliName.code == code, KbliName.version == ver)).first()
            names[k] = nm or ""
        out.update(status="Tidak Bisa", kbli_dibutuhkan=[{"kode": k.split("|")[0], "versi": k.split("|")[1], "nama": n} for k, n in names.items()],
                   catatan="Perusahaan belum punya KBLI yang sesuai. Salah satu KBLI di atas diperlukan.")
    return out

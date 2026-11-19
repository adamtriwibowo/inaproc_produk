"""Kelayakan kategori terhadap KBLI perusahaan. Aturan: Bisa <=> ada 'kode|versi' KBLI perusahaan di kbli_codes kategori."""
from collections import Counter, defaultdict

from sqlmodel import Session, select

from ..models import Category, CompanyKbli, CompanyProductCount, KbliName

_cache = {"cats": None}


def invalidate():
    _cache["cats"] = None


def all_categories(s: Session) -> list[Category]:
    if _cache["cats"] is None:
        _cache["cats"] = list(s.exec(select(Category)).all())
    return _cache["cats"]


def kbli_set(s: Session, company_id: int) -> set:
    return {f"{k.code}|{k.version}" for k in s.exec(select(CompanyKbli).where(CompanyKbli.company_id == company_id))}


def matched(cat: Category, kset: set) -> list:
    return [k for k in cat.kbli_codes if k in kset]


def is_ok(cat: Category, kset: set) -> bool:
    return any(k in kset for k in cat.kbli_codes)


def status_label(ok: int, total: int) -> str:
    if total == 0 or ok == 0:
        return "Tidak Bisa"
    return "Bisa" if ok == total else "Sebagian"


def build_tree(s: Session, company_id: int, existing: dict | None = None) -> dict:
    kset = kbli_set(s, company_id)
    cats = all_categories(s)
    l1s: dict = {}
    for c in cats:
        ok = is_ok(c, kset)
        n1 = l1s.setdefault(c.l1, {"name": c.l1, "ok": 0, "no": 0, "children": {}})
        n2 = n1["children"].setdefault(c.l2, {"name": c.l2, "ok": 0, "no": 0, "children": []})
        key = "ok" if ok else "no"
        n1[key] += 1
        n2[key] += 1
        n2["children"].append({
            "id": c.id, "name": c.l3, "ok": ok, "jenis": c.product_type, "uuid": c.uuid,
            "existing": (existing or {}).get(c.l3, 0),
        })
    out = []
    for n1 in sorted(l1s.values(), key=lambda x: x["name"].lower()):
        subs = []
        for n2 in sorted(n1["children"].values(), key=lambda x: x["name"].lower()):
            n2["status"] = status_label(n2["ok"], n2["ok"] + n2["no"])
            n2["children"].sort(key=lambda x: x["name"].lower())
            subs.append(n2)
        n1["children"] = subs
        n1["status"] = status_label(n1["ok"], n1["ok"] + n1["no"])
        out.append(n1)
    return {
        "tree": out,
        "totals": summary_from_tree(out),
    }


def summary_from_tree(tree: list) -> dict:
    ok = sum(n["ok"] for n in tree)
    no = sum(n["no"] for n in tree)
    subs = [s for n in tree for s in n["children"]]
    return {
        "kategori_bisa": ok, "kategori_tidak_bisa": no, "kategori_total": ok + no,
        "sub_bisa": sum(1 for x in subs if x["status"] == "Bisa"),
        "sub_sebagian": sum(1 for x in subs if x["status"] == "Sebagian"),
        "sub_tidak": sum(1 for x in subs if x["status"] == "Tidak Bisa"),
        "utama_bisa": sum(1 for x in tree if x["status"] == "Bisa"),
        "utama_sebagian": sum(1 for x in tree if x["status"] == "Sebagian"),
        "utama_tidak": sum(1 for x in tree if x["status"] == "Tidak Bisa"),
        "utama_dengan_bisa": sum(1 for x in tree if x["ok"] > 0),
    }


def existing_counts(s: Session, company_id: int) -> dict:
    out: dict = defaultdict(int)
    for r in s.exec(select(CompanyProductCount).where(CompanyProductCount.company_id == company_id)):
        out[r.l3] += r.count
    return dict(out)


def category_detail(s: Session, company_id: int, cat: Category) -> dict:
    kset = kbli_set(s, company_id)
    names = {(k.code, k.version): k.name for k in s.exec(select(KbliName))}
    rows = []
    for k in cat.kbli_codes:
        code, ver = k.split("|")
        rows.append({"code": code, "version": ver, "name": names.get((code, ver), ""), "milik": k in kset})
    rows.sort(key=lambda r: (r["version"], r["code"]))
    return {
        "id": cat.id, "l1": cat.l1, "l2": cat.l2, "l3": cat.l3, "jenis": cat.product_type, "uuid": cat.uuid,
        "ok": is_ok(cat, kset), "kbli": rows,
        "kbli_cocok": [r for r in rows if r["milik"]],
    }


def kbli_ranking(s: Session, company_id: int, limit: int = 15) -> list:
    """KBLI (belum dimiliki perusahaan) yang paling banyak membuka kategori 'Tidak Bisa'."""
    kset = kbli_set(s, company_id)
    names = {f"{k.code}|{k.version}": k.name for k in s.exec(select(KbliName))}
    cnt: Counter = Counter()
    for c in all_categories(s):
        if is_ok(c, kset):
            continue
        for k in c.kbli_codes:
            cnt[k] += 1
    out = []
    for k, n in cnt.most_common(limit):
        code, ver = k.split("|")
        out.append({"code": code, "version": ver, "name": names.get(k, ""), "kategori": n})
    return out


def kbli_openings(s: Session, company_id: int) -> dict:
    """Jumlah kategori yang dibuka tiap KBLI perusahaan."""
    kset = kbli_set(s, company_id)
    cnt: Counter = Counter()
    for c in all_categories(s):
        for k in c.kbli_codes:
            if k in kset:
                cnt[k] += 1
    return dict(cnt)


FLAGS = [
    (("Alat Kesehatan", "Peralatan Kesehatan", "Jasa Bidang Kesehatan"), "Butuh izin edar alkes (Kemenkes)"),
    (("Alat Berat",), "Alat berat: pastikan legalitas dan dokumen unit"),
    (("Meteorologi", "Klimatologi", "Geofisika", "MKG", "Modifikasi Cuaca"), "Bidang BMKG: biasanya perlu rekomendasi/izin BMKG"),
    (("Software", "Perangkat Lunak"), "Reseller software: perlu bukti keagenan/lisensi resmi"),
]


def flag_for(cat: Category) -> list:
    text = f"{cat.l1} {cat.l2} {cat.l3}"
    return [msg for keys, msg in FLAGS if any(k.lower() in text.lower() for k in keys)]


def rekomendasi(s: Session, company_id: int, template_l3: set) -> list:
    """Kategori 'Bisa' yang belum punya produk. Prioritas 1: subkategori terisi, 2: kategori utama terisi, 3: kategori utama baru."""
    kset = kbli_set(s, company_id)
    cats = all_categories(s)
    ex = existing_counts(s, company_id)
    filled_l3 = {n for n, v in ex.items() if v > 0}
    filled_l2, filled_l1 = set(), set()
    for c in cats:
        if c.l3 in filled_l3:
            filled_l2.add((c.l1, c.l2))
            filled_l1.add(c.l1)
    out = []
    for c in cats:
        if not is_ok(c, kset) or c.l3 in filled_l3:
            continue
        pr = 1 if (c.l1, c.l2) in filled_l2 else 2 if c.l1 in filled_l1 else 3
        out.append({
            "id": c.id, "l1": c.l1, "l2": c.l2, "l3": c.l3, "jenis": c.product_type, "prioritas": pr,
            "flags": flag_for(c), "punya_template": c.l3 in template_l3,
        })
    out.sort(key=lambda r: (r["prioritas"], r["l1"].lower(), r["l2"].lower(), r["l3"].lower()))
    return out


def existing_warnings(s: Session, company_id: int) -> list:
    """Produk existing yang kategorinya kini 'Tidak Bisa' (semua kategori ber-nama itu tidak lolos KBLI)."""
    kset = kbli_set(s, company_id)
    by_name: dict = defaultdict(list)
    for c in all_categories(s):
        by_name[c.l3].append(c)
    out = []
    for name, n in existing_counts(s, company_id).items():
        cs = by_name.get(name)
        if cs and not any(is_ok(c, kset) for c in cs):
            out.append({"l3": name, "jumlah": n, "kategori": [f"{c.l1} › {c.l2}" for c in cs]})
    return out

"""Harga jual dihitung KODE dari harga beli + aturan perusahaan. AI tidak menentukan harga."""
import math

from sqlmodel import Session, select

from ..models import PricingRule

SPECIFICITY = {"l3": 3, "l2": 2, "l1": 1, "semua": 0}


def pick_rule(rules: list, l1: str, l2: str, l3: str):
    best, best_sp = None, -1
    for r in rules:
        ok = (r.scope == "semua") or (r.scope == "l1" and r.category_name == l1) \
            or (r.scope == "l2" and r.category_name == l2) or (r.scope == "l3" and r.category_name == l3)
        sp = SPECIFICITY.get(r.scope, 0)
        if ok and sp > best_sp:
            best, best_sp = r, sp
    return best


def compute_price(cost: int | None, rule) -> int | None:
    """Tanpa harga beli -> None (kolom harga kosong, wajib diisi manusia). Tanpa aturan -> None juga:
    markup tidak boleh ditebak."""
    if not cost or cost <= 0 or rule is None:
        return None
    price = cost * (1 + (rule.markup_pct or 0) / 100.0)
    if rule.rounding and rule.rounding > 0:
        price = math.ceil(price / rule.rounding - 1e-9) * rule.rounding     # bulatkan ke atas ke kelipatan
    price = int(round(price))
    if rule.min_price and price < rule.min_price:
        price = int(rule.min_price)
    return price


def rules_of(s: Session, company_id: int) -> list:
    return list(s.exec(select(PricingRule).where(PricingRule.company_id == company_id)))

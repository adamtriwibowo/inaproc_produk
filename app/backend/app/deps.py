"""Dependency: autentikasi dan akses per perusahaan (keanggotaan + role). Dipakai di SETIAP endpoint perusahaan."""
from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException
from sqlmodel import Session, select

from .db import get_session
from .models import AuditLog, Company, Membership, User
from .security import read_token

ROLES = ("admin", "operator", "reviewer")
ROLE_LABEL = {"admin": "Admin Perusahaan", "operator": "Operator Input", "reviewer": "Reviewer"}


def current_user(
    authorization: str | None = Header(default=None),
    token: str | None = Cookie(default=None),
    s: Session = Depends(get_session),
) -> User:
    tok = None
    if authorization and authorization.lower().startswith("bearer "):
        tok = authorization[7:].strip()
    tok = tok or token
    uid = read_token(tok) if tok else None
    user = s.get(User, uid) if uid else None
    if not user or not user.active:
        raise HTTPException(401, "Belum login atau sesi berakhir")
    return user


def require_super(user: User = Depends(current_user)) -> User:
    if not user.is_super:
        raise HTTPException(403, "Hanya Super Admin")
    return user


@dataclass
class Ctx:
    user: User
    company: Company
    role: str          # peran efektif di perusahaan ini
    session: Session


def company_ctx(company_id: int, user: User = Depends(current_user), s: Session = Depends(get_session)) -> Ctx:
    """Perusahaan yang tidak boleh diakses -> 404 (tidak membocorkan keberadaannya)."""
    comp = s.get(Company, company_id)
    if not comp:
        raise HTTPException(404, "Perusahaan tidak ditemukan")
    if user.is_super:
        role = "admin"
    else:
        m = s.exec(select(Membership).where(Membership.user_id == user.id, Membership.company_id == company_id)).first()
        if not m:
            raise HTTPException(404, "Perusahaan tidak ditemukan")
        role = m.role
    if not comp.active and not user.is_super:
        raise HTTPException(403, "Perusahaan dinonaktifkan")
    return Ctx(user=user, company=comp, role=role, session=s)


def need(*roles: str):
    """Dependency pembatas role: need('admin','reviewer')."""
    def dep(ctx: Ctx = Depends(company_ctx)) -> Ctx:
        if ctx.role not in roles:
            raise HTTPException(403, f"Peran Anda ({ROLE_LABEL.get(ctx.role, ctx.role)}) tidak boleh melakukan ini")
        return ctx
    return dep


any_member = need(*ROLES)


def audit(s: Session, user: User | None, company_id: int | None, action: str, detail: str = ""):
    s.add(AuditLog(company_id=company_id, user_id=user.id if user else None,
                   user_email=user.email if user else "", action=action, detail=detail))
    s.commit()

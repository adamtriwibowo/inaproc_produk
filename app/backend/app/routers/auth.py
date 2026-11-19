from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import config
from ..db import get_session
from ..deps import ROLE_LABEL, audit, current_user
from ..models import Company, Membership, User
from ..security import hash_password, make_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class PwIn(BaseModel):
    old_password: str
    new_password: str


def me_payload(s: Session, user: User) -> dict:
    if user.is_super:
        comps = s.exec(select(Company)).all()
        mem = [{"company_id": c.id, "role": "admin", "role_label": "Super Admin"} for c in comps]
    else:
        mem = []
        for m in s.exec(select(Membership).where(Membership.user_id == user.id)):
            c = s.get(Company, m.company_id)
            if c and c.active:
                mem.append({"company_id": c.id, "role": m.role, "role_label": ROLE_LABEL[m.role]})
        comps = [s.get(Company, m["company_id"]) for m in mem]
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name, "is_super": user.is_super},
        "memberships": mem,
        "companies": [{"id": c.id, "name": c.name, "store_name": c.store_name, "institution_id": c.institution_id,
                       "logo": c.logo, "active": c.active} for c in comps],
    }


@router.post("/login")
def login(body: LoginIn, resp: Response, s: Session = Depends(get_session)):
    user = s.exec(select(User).where(User.email == body.email.strip().lower())).first()
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email atau password salah")
    tok = make_token(user.id)
    resp.set_cookie("token", tok, httponly=True, samesite="lax", secure=config.COOKIE_SECURE,
                    max_age=config.TOKEN_HOURS * 3600)
    audit(s, user, None, "login")
    return {"token": tok, **me_payload(s, user)}


@router.post("/logout")
def logout(resp: Response):
    resp.delete_cookie("token")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), s: Session = Depends(get_session)):
    return me_payload(s, user)


@router.post("/change-password")
def change_password(body: PwIn, user: User = Depends(current_user), s: Session = Depends(get_session)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Password lama salah")
    if len(body.new_password) < 8:
        raise HTTPException(400, "Password baru minimal 8 karakter")
    user.password_hash = hash_password(body.new_password)
    s.add(user)
    s.commit()
    return {"ok": True}

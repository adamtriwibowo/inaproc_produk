"""Super Admin: perusahaan, pengguna, keanggotaan, ringkasan lintas perusahaan."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, func

from ..db import get_session
from ..deps import ROLES, audit, require_super
from ..models import Batch, Company, Membership, User
from ..security import hash_password
from ..services import kelayakan

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_super)])


class CompanyIn(BaseModel):
    name: str
    store_name: str = ""
    inaproc_email: str = ""
    institution_id: str
    scale: str = ""
    logo: str = ""
    active: bool = True


class UserIn(BaseModel):
    email: str
    name: str = ""
    password: str
    is_super: bool = False


class MemberIn(BaseModel):
    user_id: int
    company_id: int
    role: str


def comp_dict(c: Company) -> dict:
    return c.model_dump(mode="json")


@router.get("/companies")
def list_companies(s: Session = Depends(get_session)):
    return [comp_dict(c) for c in s.exec(select(Company).order_by(Company.name))]


@router.post("/companies")
def create_company(body: CompanyIn, user: User = Depends(require_super), s: Session = Depends(get_session)):
    if not body.name.strip() or not body.institution_id.strip():
        raise HTTPException(400, "Nama dan Institution ID wajib")
    if s.exec(select(Company).where(Company.institution_id == body.institution_id.strip())).first():
        raise HTTPException(409, "Institution ID sudah terdaftar")
    c = Company(**{**body.model_dump(), "institution_id": body.institution_id.strip()})
    s.add(c)
    s.commit()
    s.refresh(c)
    audit(s, user, c.id, "perusahaan.buat", c.name)
    return comp_dict(c)


@router.patch("/companies/{cid}")
def update_company(cid: int, body: dict, user: User = Depends(require_super), s: Session = Depends(get_session)):
    c = s.get(Company, cid)
    if not c:
        raise HTTPException(404, "Perusahaan tidak ditemukan")
    for k in ("name", "store_name", "inaproc_email", "scale", "logo", "active"):
        if k in body:
            setattr(c, k, body[k])
    s.add(c)
    s.commit()
    audit(s, user, cid, "perusahaan.ubah", ",".join(body.keys()))
    return comp_dict(c)


@router.get("/users")
def list_users(s: Session = Depends(get_session)):
    out = []
    for u in s.exec(select(User).order_by(User.email)):
        ms = s.exec(select(Membership).where(Membership.user_id == u.id)).all()
        out.append({"id": u.id, "email": u.email, "name": u.name, "is_super": u.is_super, "active": u.active,
                    "memberships": [{"company_id": m.company_id, "role": m.role} for m in ms]})
    return out


@router.post("/users")
def create_user(body: UserIn, user: User = Depends(require_super), s: Session = Depends(get_session)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Email tidak valid")
    if len(body.password) < 8:
        raise HTTPException(400, "Password minimal 8 karakter")
    if s.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "Email sudah terdaftar")
    u = User(email=email, name=body.name, password_hash=hash_password(body.password), is_super=body.is_super)
    s.add(u)
    s.commit()
    s.refresh(u)
    audit(s, user, None, "pengguna.buat", email)
    return {"id": u.id, "email": u.email}


@router.patch("/users/{uid}")
def update_user(uid: int, body: dict, user: User = Depends(require_super), s: Session = Depends(get_session)):
    u = s.get(User, uid)
    if not u:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    if "active" in body:
        if u.id == user.id and not body["active"]:
            raise HTTPException(400, "Tidak bisa menonaktifkan diri sendiri")
        u.active = bool(body["active"])
    if "name" in body:
        u.name = body["name"]
    if body.get("password"):
        if len(body["password"]) < 8:
            raise HTTPException(400, "Password minimal 8 karakter")
        u.password_hash = hash_password(body["password"])
    s.add(u)
    s.commit()
    audit(s, user, None, "pengguna.ubah", u.email)
    return {"ok": True}


@router.put("/memberships")
def set_membership(body: MemberIn, user: User = Depends(require_super), s: Session = Depends(get_session)):
    if body.role not in ROLES:
        raise HTTPException(400, "Role tidak valid")
    if not s.get(User, body.user_id) or not s.get(Company, body.company_id):
        raise HTTPException(404, "Pengguna/perusahaan tidak ditemukan")
    m = s.exec(select(Membership).where(Membership.user_id == body.user_id, Membership.company_id == body.company_id)).first()
    if m:
        m.role = body.role
    else:
        m = Membership(**body.model_dump())
    s.add(m)
    s.commit()
    audit(s, user, body.company_id, "anggota.set", f"user {body.user_id} -> {body.role}")
    return {"ok": True}


@router.delete("/memberships")
def del_membership(user_id: int, company_id: int, user: User = Depends(require_super), s: Session = Depends(get_session)):
    m = s.exec(select(Membership).where(Membership.user_id == user_id, Membership.company_id == company_id)).first()
    if m:
        s.delete(m)
        s.commit()
        audit(s, user, company_id, "anggota.cabut", f"user {user_id}")
    return {"ok": True}


@router.get("/overview")
def overview(s: Session = Depends(get_session)):
    out = []
    for c in s.exec(select(Company).order_by(Company.name)):
        tree = kelayakan.build_tree(s, c.id)["totals"]
        by_status = {st: n for st, n in s.exec(
            select(Batch.status, func.count()).where(Batch.company_id == c.id).group_by(Batch.status))}
        out.append({"id": c.id, "name": c.name, "active": c.active, "kategori_bisa": tree["kategori_bisa"],
                    "kategori_tidak_bisa": tree["kategori_tidak_bisa"], "batch": by_status})
    return out

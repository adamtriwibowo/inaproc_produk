from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from . import config


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=config.TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def read_token(tok: str):
    try:
        return int(jwt.decode(tok, config.SECRET_KEY, algorithms=["HS256"])["sub"])
    except Exception:
        return None

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="inaproc_test_")
os.environ["INAPROC_STORAGE_DIR"] = _tmp
os.environ["INAPROC_ADMIN_EMAIL"] = "admin@test.local"
os.environ["INAPROC_ADMIN_PASSWORD"] = "Admin-Test-123"
os.environ["INAPROC_SEED"] = "1"
os.environ["INAPROC_AI_SYNC"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db, session_scope  # noqa: E402
from app.services.seed import run_seed  # noqa: E402

init_db()
with session_scope() as _s:
    run_seed(_s)

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session():
    with session_scope() as s:
        yield s


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return login(client, "admin@test.local", "Admin-Test-123")

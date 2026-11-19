from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import init_db, session_scope


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if config.SEED_ON_START:
        from .services.seed import run_seed
        with session_scope() as s:
            run_seed(s)
    yield


app = FastAPI(title="INAPROC Bulk Upload Assistant", lifespan=lifespan)

from .routers import admin, auth, batches, company, kelayakan, photos, templates  # noqa: E402

for r in (auth.router, admin.router, company.router, kelayakan.router, templates.router, batches.router, photos.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}


# Frontend hasil build (opsional; dipakai di Docker)
_static = Path(__file__).resolve().parent.parent / "static"
if _static.exists():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = _static / path
        return FileResponse(f if path and f.is_file() else _static / "index.html")

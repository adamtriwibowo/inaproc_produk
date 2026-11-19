"""Job latar belakang (thread pool di dalam proses). Job yang terputus karena restart ditandai gagal dan bisa diulang."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from sqlmodel import select

from ..db import session_scope
from ..models import AiJob
from .ai_client import AiError

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-job")
RUN_SYNC = os.environ.get("INAPROC_AI_SYNC", "0") == "1"   # test: jalankan di thread pemanggil


def _run(job_id: int, fn):
    with session_scope() as s:
        job = s.get(AiJob, job_id)
        try:
            fn(s, job)
        except AiError as e:
            job.status, job.message = "gagal", str(e)[:500]
        except Exception as e:  # noqa: BLE001  galat tak terduga: jangan bocorkan detail internal
            job.status, job.message = "gagal", f"Galat tak terduga ({type(e).__name__})."
        else:
            return
        job.finished_at = datetime.now(timezone.utc)
        s.add(job)
        s.commit()


def submit(job_id: int, fn):
    if RUN_SYNC:
        _run(job_id, fn)
    else:
        _pool.submit(_run, job_id, fn)


def fail_interrupted():
    """Dipanggil saat server start."""
    with session_scope() as s:
        for j in s.exec(select(AiJob).where(AiJob.status.in_(("antri", "berjalan")))):
            j.status, j.message = "gagal", "Terputus karena server dimulai ulang. Jalankan ulang."
            j.finished_at = datetime.now(timezone.utc)
            s.add(j)
        s.commit()

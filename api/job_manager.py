"""
Minimal in-memory job manager for background pipeline tasks.

This is intentionally simple (no Redis/Celery) since the vault is a local,
single-user application. Jobs live in a process-wide dict and are driven by
a plain Python thread. Good enough for one machine, one user, one job at a
time per type.
"""
import threading
import time
import uuid
from typing import Callable, Optional

_jobs: dict = {}
_lock = threading.Lock()


def create_job(job_type: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "status": "running",     # running | done | error
            "progress": 0,
            "total": 0,
            "current_item": None,
            "started_at": time.time(),
            "finished_at": None,
            "result": None,
            "error": None,
        }
    return job_id


def update_job(job_id: str, **fields):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def get_job(job_id: str) -> Optional[dict]:
    with _lock:
        return dict(_jobs[job_id]) if job_id in _jobs else None


def list_jobs() -> list:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)


def run_in_background(job_id: str, target: Callable, *args, **kwargs):
    def _runner():
        try:
            result = target(*args, **kwargs)
            update_job(job_id, status="done", result=result, finished_at=time.time())
        except Exception as e:
            update_job(job_id, status="error", error=str(e), finished_at=time.time())

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

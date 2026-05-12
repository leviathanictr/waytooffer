"""In-memory job store for background AI tasks."""
from __future__ import annotations

import threading
import uuid
from typing import Literal


class Job:
    def __init__(self) -> None:
        self.status: Literal["processing", "done", "error"] = "processing"
        self.content: str = ""
        self.is_complete: bool = False
        self.error: str | None = None
        self.result: dict | None = None
        self._lock = threading.Lock()

    def append(self, delta: str) -> None:
        with self._lock:
            self.content += delta

    def finish(self, is_complete: bool, result: dict | None = None) -> None:
        with self._lock:
            self.status = "done"
            self.is_complete = is_complete
            self.result = result

    def fail(self, error: str) -> None:
        with self._lock:
            self.status = "error"
            self.error = error

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "content": self.content,
                "is_complete": self.is_complete,
                "error": self.error,
                "result": self.result,
            }


_store: dict[str, Job] = {}
_store_lock = threading.Lock()


def create() -> tuple[str, Job]:
    job_id = str(uuid.uuid4())
    job = Job()
    with _store_lock:
        _store[job_id] = job
    return job_id, job


def get(job_id: str) -> Job | None:
    with _store_lock:
        return _store.get(job_id)

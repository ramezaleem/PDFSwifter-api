from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Optional


@dataclass
class DownloadJob:
    process_id: str
    source: str
    url: str
    status: str = "pending"
    progress: float = 0.0
    bytes_downloaded: int = 0
    total_bytes: Optional[int] = None
    file_path: Optional[str] = None
    suggested_name: Optional[str] = None
    error: Optional[str] = None


class DownloadTracker:
    def __init__(self) -> None:
        self._jobs: Dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def create_job(self, source: str, url: str) -> DownloadJob:
        process_id = uuid.uuid4().hex
        job = DownloadJob(process_id=process_id, source=source, url=url)
        with self._lock:
            self._jobs[process_id] = job
        return job

    def get_job(self, process_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self._jobs.get(process_id)

    def update_job(self, process_id: str, **updates) -> None:
        with self._lock:
            job = self._jobs.get(process_id)
            if not job:
                return
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)

    def serialize_job(self, process_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            job = self._jobs.get(process_id)
            if not job:
                return None
            payload = asdict(job)
        if payload.get("file_path"):
            payload["file_exists"] = os.path.exists(payload["file_path"])
        else:
            payload["file_exists"] = False
        return payload

    def protected_file_paths(self) -> set[str]:
        """Return file paths that should not be deleted yet (best-effort)."""
        protected: set[str] = set()
        with self._lock:
            for job in self._jobs.values():
                if job.status in {"pending", "running"} and job.file_path:
                    protected.add(job.file_path)
        return protected


DOWNLOAD_TRACKER = DownloadTracker()

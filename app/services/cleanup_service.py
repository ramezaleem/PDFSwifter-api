from __future__ import annotations

import os
import shutil
import threading
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set, Tuple


@dataclass(frozen=True)
class CleanupStats:
    files_deleted: int = 0
    dirs_deleted: int = 0
    errors: int = 0


class CleanupService:
    def __init__(
        self,
        retention_by_folder: Dict[str, int],
        interval_seconds: int,
        protected_paths_provider: Optional[callable] = None,
    ) -> None:
        self._retention_by_folder = dict(retention_by_folder)
        self._interval_seconds = max(int(interval_seconds), 5)
        self._protected_paths_provider = protected_paths_provider

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def cleanup_once(self) -> CleanupStats:
        protected_paths = self._get_protected_paths()
        now = time.time()

        files_deleted = 0
        dirs_deleted = 0
        errors = 0

        for root, ttl_seconds in self._iter_roots():
            if ttl_seconds <= 0:
                continue
            cutoff = now - ttl_seconds

            if not os.path.isdir(root):
                continue

            # Delete old files
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.abspath(file_path) in protected_paths:
                        continue
                    try:
                        stat = os.stat(file_path)
                        if stat.st_mtime < cutoff:
                            os.remove(file_path)
                            files_deleted += 1
                    except FileNotFoundError:
                        continue
                    except Exception:
                        errors += 1

            # Remove empty directories (bottom-up), but never remove the root itself.
            for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                if dirpath == root:
                    continue
                if dirnames or filenames:
                    continue
                try:
                    stat = os.stat(dirpath)
                    if stat.st_mtime < cutoff:
                        shutil.rmtree(dirpath, ignore_errors=True)
                        dirs_deleted += 1
                except FileNotFoundError:
                    continue
                except Exception:
                    errors += 1

        return CleanupStats(files_deleted=files_deleted, dirs_deleted=dirs_deleted, errors=errors)

    def _run_loop(self) -> None:
        # Initial short delay so startup can finish quickly.
        self._stop_event.wait(timeout=1.0)
        while not self._stop_event.is_set():
            try:
                self.cleanup_once()
            except Exception:
                # Never crash the background thread.
                pass
            self._stop_event.wait(timeout=self._interval_seconds)

    def _iter_roots(self) -> Iterable[Tuple[str, int]]:
        for root, ttl in self._retention_by_folder.items():
            yield root, int(ttl)

    def _get_protected_paths(self) -> Set[str]:
        if not self._protected_paths_provider:
            return set()
        try:
            protected = self._protected_paths_provider()
            return {os.path.abspath(p) for p in protected if p}
        except Exception:
            return set()

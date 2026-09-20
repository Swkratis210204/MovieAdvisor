"""Simple on-disk JSON cache keyed by string keys (e.g. API URLs)."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_DIR = Path(os.environ.get("CACHE_DIR", ".cache"))
DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 days


class DiskCache:
    """On-disk cache that degrades to a no-op instead of crashing if the
    filesystem is unwritable (e.g. a read-only container filesystem)."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl: int = DEFAULT_TTL_SECONDS):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.enabled = True
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.enabled = False

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - payload.get("_cached_at", 0) > self.ttl:
            return None
        return payload.get("data")

    def set(self, key: str, data: Any) -> None:
        if not self.enabled:
            return
        path = self._path_for(key)
        payload = {"_cached_at": time.time(), "data": data}
        tmp_path = path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(tmp_path, path)
        except OSError:
            self.enabled = False

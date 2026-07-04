"""A tiny thread-safe TTL + LRU cache.

Why not `functools.lru_cache`? We need TTL expiry (a review result shouldn't
live forever) and a cache key derived from a hash of (code, language, provider
preference) rather than raw arguments. This is deliberately dependency-free
(no Redis) because the assignment is a single-process API; swapping this for
a Redis-backed implementation later only requires changing this one module,
since callers only see `get` / `set`.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class TTLCache:
    def __init__(self, max_entries: int = 512, ttl_seconds: int = 900) -> None:
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._store: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def make_key(*parts: str) -> str:
        digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
        return digest

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                del self._store[key]
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl_seconds, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    def stats(self) -> dict:
        with self._lock:
            return {"size": len(self._store), "hits": self.hits, "misses": self.misses}

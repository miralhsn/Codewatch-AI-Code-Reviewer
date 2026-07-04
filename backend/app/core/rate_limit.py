"""Per-client sliding-window rate limiter.

Keeps the API from being hammered (accidentally or otherwise) since every
request can trigger an expensive LLM call. In-memory is fine for a single
process; behind multiple workers you'd back this with Redis, but the
interface (`allow(client_id)`) would not need to change.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[client_id]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                retry_after = int(self._window - (now - bucket[0])) + 1
                return False, retry_after
            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: SlidingWindowRateLimiter, exempt_paths: set[str] | None = None):
        super().__init__(app)
        self._limiter = limiter
        self._exempt = exempt_paths or {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt:
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        allowed, retry_after = self._limiter.allow(client_id)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

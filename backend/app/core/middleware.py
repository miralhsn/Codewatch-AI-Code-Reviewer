from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .logging import log_extra, logger, request_id_ctx


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id (or reuses an inbound one) and logs timing."""

    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("x-request-id")
        request_id = incoming_id or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "Unhandled exception",
                extra=log_extra(path=request.url.path, duration_ms=duration_ms),
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.info(
                "request completed",
                extra=log_extra(
                    path=request.url.path,
                    method=request.method,
                    status=response.status_code,
                    duration_ms=duration_ms,
                ),
            )
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)

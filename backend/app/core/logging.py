"""Structured logging configuration.

Emits single-line JSON records so logs are greppable and ingestible by any
log aggregator (Datadog, CloudWatch, Loki, ...) without extra parsing rules.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("ai_code_reviewer")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def log_extra(**fields) -> dict:
    """Helper to attach structured fields: logger.info("msg", extra=log_extra(x=1))"""
    return {"extra_fields": fields}

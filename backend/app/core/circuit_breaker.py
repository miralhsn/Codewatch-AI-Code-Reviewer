"""A minimal per-provider circuit breaker.

The original project retried OpenAI -> Ollama -> fallback on *every single
request*, even when OpenAI had been down for the last 50 requests in a row.
That wastes the full request timeout on a provider we already know is
unhealthy. A circuit breaker remembers recent failures and, once a threshold
is crossed, skips the provider for a cooldown window instead of calling it
again -- so requests fail fast to the next provider in the chain.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _BreakerState:
    failure_count: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 60) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._states: dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def _state(self, name: str) -> _BreakerState:
        return self._states.setdefault(name, _BreakerState())

    def is_open(self, name: str) -> bool:
        with self._lock:
            state = self._state(name)
            if state.opened_at is None:
                return False
            if time.monotonic() - state.opened_at >= self._cooldown:
                # Cooldown elapsed: allow a single trial call (half-open).
                state.opened_at = None
                state.failure_count = 0
                return False
            return True

    def record_success(self, name: str) -> None:
        with self._lock:
            state = self._state(name)
            state.failure_count = 0
            state.opened_at = None

    def record_failure(self, name: str) -> None:
        with self._lock:
            state = self._state(name)
            state.failure_count += 1
            if state.failure_count >= self._threshold and state.opened_at is None:
                state.opened_at = time.monotonic()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                name: {
                    "open": state.opened_at is not None,
                    "failure_count": state.failure_count,
                }
                for name, state in self._states.items()
            }

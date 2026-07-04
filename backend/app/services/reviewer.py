from __future__ import annotations

import time

from ..core.cache import TTLCache
from ..core.circuit_breaker import CircuitBreaker
from ..core.config import Settings
from ..core.exceptions import CodeTooLargeError, ReviewError
from ..core.logging import log_extra, logger
from ..schemas.review import CodeReviewResponse, ReviewMetadata
from .base import ReviewProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .static_analyzer import StaticAnalysisProvider


class ReviewOrchestrator:
    """Runs the provider chain with caching and a circuit breaker per provider.

    Compared to the original `ai_router.get_ai_review`, which was a flat
    function calling three hardcoded modules in sequence, this class:
      * Skips a provider outright while its circuit breaker is open, instead
        of paying its full timeout on every request during an outage.
      * Caches identical (code, language) requests so re-submitting the same
        snippet -- common while iterating in the UI -- doesn't re-spend an
        LLM call.
      * Lets the caller optionally reorder the chain (`prefer_provider`)
        without duplicating the fallback logic.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._cache = TTLCache(max_entries=settings.cache_max_entries, ttl_seconds=settings.cache_ttl_seconds)
        self._breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
        )
        self._providers: dict[str, ReviewProvider] = {
            "openai": OpenAIProvider(settings),
            "ollama": OllamaProvider(settings),
        }
        self._fallback = StaticAnalysisProvider()

    def _ordered_provider_names(self, prefer: str | None) -> list[str]:
        names = ["openai", "ollama"]
        if prefer and prefer in names:
            names.remove(prefer)
            names.insert(0, prefer)
        return names

    def review(self, code: str, language: str, prefer_provider: str | None, request_id: str) -> CodeReviewResponse:
        if len(code) > self._settings.max_code_length_chars:
            raise CodeTooLargeError(
                f"Code is {len(code)} characters, which exceeds the {self._settings.max_code_length_chars} limit."
            )

        cache_key = TTLCache.make_key(code, language, prefer_provider or "")
        start = time.perf_counter()
        cached = self._cache.get(cache_key)
        if cached is not None:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            cached = cached.model_copy(
                update={"metadata": ReviewMetadata(request_id=request_id, latency_ms=latency_ms, cached=True, attempts=[])}
            )
            return cached

        attempts: list[str] = []
        for name in self._ordered_provider_names(prefer_provider):
            provider = self._providers[name]
            if self._breaker.is_open(name):
                logger.info("skipping provider: circuit open", extra=log_extra(provider=name))
                attempts.append(f"{name}(circuit-open)")
                continue
            attempts.append(name)
            try:
                result = provider.review(code=code, language=language)
                self._breaker.record_success(name)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                result = result.model_copy(
                    update={
                        "metadata": ReviewMetadata(
                            request_id=request_id, latency_ms=latency_ms, cached=False, attempts=attempts
                        )
                    }
                )
                self._cache.set(cache_key, result)
                return result
            except ReviewError as exc:
                self._breaker.record_failure(name)
                logger.warning("provider failed", extra=log_extra(provider=name, error=str(exc)))
            except Exception as exc:  # defensive: never let one bad provider crash the request
                self._breaker.record_failure(name)
                logger.exception("provider raised unexpected error", extra=log_extra(provider=name))

        # Fallback always succeeds; it has no external dependency to fail.
        attempts.append("fallback")
        result = self._fallback.review(code=code, language=language)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        result = result.model_copy(
            update={
                "metadata": ReviewMetadata(request_id=request_id, latency_ms=latency_ms, cached=False, attempts=attempts)
            }
        )
        self._cache.set(cache_key, result)
        return result

    def cache_stats(self) -> dict:
        return self._cache.stats()

    def breaker_snapshot(self) -> dict:
        return self._breaker.snapshot()

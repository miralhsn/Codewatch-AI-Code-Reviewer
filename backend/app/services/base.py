from __future__ import annotations

from typing import Protocol

from ..schemas.review import CodeReviewResponse


class ReviewProvider(Protocol):
    """Every review backend (OpenAI, Ollama, static-analysis fallback)
    implements this single method, so the router can treat them
    interchangeably and the list of providers is just data, not a chain of
    hardcoded `try/except` blocks."""

    name: str

    def review(self, code: str, language: str) -> CodeReviewResponse: ...

from __future__ import annotations

import time

import requests

from ..core.config import Settings
from ..core.exceptions import ProviderDisabledError, ProviderResponseError, ProviderUnavailableError
from ..core.logging import log_extra, logger
from ..prompts.review_prompt import build_review_prompt, build_self_check_prompt
from ..schemas.review import CodeReviewResponse
from .validation import build_response, parse_and_validate_response

_FORMAT_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "severity": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "line": {"type": ["integer", "null"]},
                },
                "required": ["category", "severity", "title", "description"],
            },
        },
        "refactored_code": {"type": "string"},
        "diff": {"type": "string"},
        "explanation": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["findings", "refactored_code", "diff", "explanation", "confidence"],
}


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings):
        self._settings = settings

    def _generate(self, prompt_text: str) -> str:
        s = self._settings
        response = requests.post(
            s.ollama_url,
            json={
                "model": s.ollama_model,
                "prompt": prompt_text,
                "stream": False,
                "temperature": 0.1,
                "format": _FORMAT_SCHEMA,
            },
            timeout=(s.ollama_connect_timeout_seconds, s.ollama_read_timeout_seconds),
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("done", True):
            raise ProviderUnavailableError("Ollama returned an incomplete response.")
        return data.get("response", "")

    def review(self, code: str, language: str) -> CodeReviewResponse:
        s = self._settings
        if not s.enable_ollama:
            raise ProviderDisabledError("Ollama is disabled by configuration.")

        last_exc: Exception | None = None
        for attempt in range(1, s.ollama_max_retries + 1):
            try:
                prompt = build_review_prompt(code=code, language=language, strict_retry=(attempt > 1))
                content = self._generate(prompt)
                checked = content
                if s.enable_self_check:
                    checked = self._generate(build_self_check_prompt(code=code, language=language, draft_json=content))
                payload = parse_and_validate_response(checked, original_code=code, language=language)
                payload["confidence"] = max(payload["confidence"], 0.75 if attempt == 1 else 0.65)
                logger.info("ollama review succeeded", extra=log_extra(attempt=attempt, model=s.ollama_model))
                return build_response(payload, used_model="ollama")
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning("ollama request failed", extra=log_extra(attempt=attempt, error=str(exc)))
            except ProviderResponseError as exc:
                last_exc = exc
                logger.warning("ollama response failed validation", extra=log_extra(attempt=attempt, error=str(exc)))

            if attempt < s.ollama_max_retries:
                time.sleep(0.8 * attempt)

        raise ProviderUnavailableError(f"Ollama failed after {s.ollama_max_retries} attempts: {last_exc}")

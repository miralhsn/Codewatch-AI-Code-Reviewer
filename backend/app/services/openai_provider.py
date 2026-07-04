from __future__ import annotations

from openai import APIError, OpenAI, RateLimitError

from ..core.config import Settings
from ..core.exceptions import ProviderDisabledError, ProviderResponseError, ProviderUnavailableError
from ..core.logging import log_extra, logger
from ..prompts.review_prompt import build_provider_messages, build_self_check_prompt
from ..schemas.review import CodeReviewResponse
from .validation import build_response, parse_and_validate_response


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: OpenAI | None = None
        if settings.enable_openai and settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)

    def _call(self, code: str, language: str, strict_retry: bool) -> str:
        assert self._client is not None
        messages = build_provider_messages(code=code, language=language, strict_retry=strict_retry)
        completion = self._client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.15,
            response_format={"type": "json_object"},
            messages=messages,
        )
        return completion.choices[0].message.content or ""

    def _self_check(self, code: str, language: str, draft_text: str) -> str:
        assert self._client is not None
        prompt = build_self_check_prompt(code=code, language=language, draft_json=draft_text)
        completion = self._client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Audit bug claims against code; return corrected JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content or ""

    def review(self, code: str, language: str) -> CodeReviewResponse:
        if not self._client:
            raise ProviderDisabledError("OpenAI is disabled or missing an API key.")

        attempts = [(False, 0.90), (True, 0.80)]
        last_error: Exception | None = None
        for strict_retry, confidence_floor in attempts:
            try:
                draft = self._call(code, language, strict_retry)
                checked = draft
                if self._settings.enable_self_check:
                    checked = self._self_check(code, language, draft)
                payload = parse_and_validate_response(checked, original_code=code, language=language)
                payload["confidence"] = max(payload["confidence"], confidence_floor)
                logger.info("openai review succeeded", extra=log_extra(strict_retry=strict_retry))
                return build_response(payload, used_model="openai")
            except (RateLimitError, APIError) as exc:
                logger.warning("openai API error", extra=log_extra(error=str(exc)))
                raise ProviderUnavailableError(str(exc)) from exc
            except ProviderResponseError as exc:
                last_error = exc
                logger.warning("openai response failed validation", extra=log_extra(error=str(exc)))

        raise ProviderResponseError(f"OpenAI failed validation after retries: {last_error}")

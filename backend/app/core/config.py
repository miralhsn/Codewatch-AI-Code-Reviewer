"""Centralized, typed application configuration.

All environment-driven behaviour lives here so the rest of the codebase
never touches `os.environ` directly. This makes settings testable
(you can construct a `Settings` object with overrides) and self-documenting
(every knob is a typed field with a default and a description).
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App metadata ---
    app_name: str = "AI Code Reviewer"
    app_version: str = "3.0.0"
    environment: str = Field(default="development", description="development | staging | production")

    # --- CORS ---
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Provider toggles ---
    enable_openai: bool = True
    enable_ollama: bool = True

    # --- OpenAI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2

    # --- Ollama ---
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama3"
    ollama_connect_timeout_seconds: float = 5.0
    ollama_read_timeout_seconds: float = 120.0
    ollama_max_retries: int = 2

    # --- Shared review behaviour ---
    enable_self_check: bool = True
    max_code_length_chars: int = 20_000

    # --- Caching ---
    cache_ttl_seconds: int = 900
    cache_max_entries: int = 512

    # --- Rate limiting ---
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60

    # --- Circuit breaker (per provider) ---
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    """Settings are cheap but process-wide constant; cache the singleton."""
    return Settings()

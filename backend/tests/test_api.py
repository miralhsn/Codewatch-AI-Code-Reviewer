import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "cache" in body
    assert "circuit_breakers" in body


def test_review_rejects_empty_code(client):
    resp = client.post("/review", json={"code": "", "language": "python"})
    assert resp.status_code == 422  # pydantic min_length=1 catches it first


def test_review_falls_back_without_llm_keys(client, monkeypatch):
    # With no OpenAI key and Ollama unreachable in CI, the orchestrator
    # should still return a usable response via the static-analysis fallback.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:1/unreachable")

    code = "def f(x):\n    if x == None:\n        return\n    print(x)\n"
    resp = client.post("/review", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_model"] == "fallback"
    assert isinstance(body["findings"], list)
    assert body["metadata"]["attempts"][-1] == "fallback"


def test_review_rejects_oversized_code(client):
    huge_code = "x = 1\n" * 20000
    resp = client.post("/review", json={"code": huge_code, "language": "python"})
    assert resp.status_code == 413


def test_static_analyzer_flags_none_comparison():
    from app.services.static_analyzer import StaticAnalysisProvider

    result = StaticAnalysisProvider().review("if x == None:\n    pass\n", "python")
    assert result.used_model == "fallback"
    assert any("is None" in f.title for f in result.findings)
    assert "is None" in result.refactored_code


def test_static_analyzer_flags_bare_except():
    from app.services.static_analyzer import StaticAnalysisProvider

    code = "try:\n    risky()\nexcept:\n    pass\n"
    result = StaticAnalysisProvider().review(code, "python")
    assert any("Bare" in f.title for f in result.findings)


def test_static_analyzer_flags_mutable_default_arg():
    from app.services.static_analyzer import StaticAnalysisProvider

    code = "def f(items=[]):\n    items.append(1)\n    return items\n"
    result = StaticAnalysisProvider().review(code, "python")
    assert any("Mutable default" in f.title for f in result.findings)


def test_cache_returns_identical_result():
    from app.core.cache import TTLCache

    cache = TTLCache(max_entries=10, ttl_seconds=60)
    key = TTLCache.make_key("code", "python", "")
    assert cache.get(key) is None
    cache.set(key, {"foo": "bar"})
    assert cache.get(key) == {"foo": "bar"}


def test_circuit_breaker_opens_after_threshold():
    from app.core.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
    assert breaker.is_open("openai") is False
    breaker.record_failure("openai")
    assert breaker.is_open("openai") is False
    breaker.record_failure("openai")
    assert breaker.is_open("openai") is True

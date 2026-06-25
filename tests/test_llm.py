import pytest

from engine.llm import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER_URL,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    get_model,
    get_provider_url,
    get_request_timeout_seconds,
    request_model,
)

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_get_model_returns_default(monkeypatch):
    monkeypatch.delenv("AI_AGENT_MODEL", raising=False)

    assert get_model() == DEFAULT_MODEL


def test_get_model_reads_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_MODEL", "custom-model")

    assert get_model() == "custom-model"


def test_get_provider_url_returns_default(monkeypatch):
    monkeypatch.delenv("AI_AGENT_PROVIDER_URL", raising=False)

    assert get_provider_url() == DEFAULT_PROVIDER_URL


def test_get_provider_url_reads_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_PROVIDER_URL", "http://example.test/api")

    assert get_provider_url() == "http://example.test/api"


def test_get_request_timeout_returns_default(monkeypatch):
    monkeypatch.delenv("AI_AGENT_REQUEST_TIMEOUT_SECONDS", raising=False)

    assert get_request_timeout_seconds() == DEFAULT_REQUEST_TIMEOUT_SECONDS


def test_get_request_timeout_reads_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_REQUEST_TIMEOUT_SECONDS", "10.5")

    assert get_request_timeout_seconds() == 10.5


def test_get_request_timeout_rejects_invalid_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_REQUEST_TIMEOUT_SECONDS", "slow")

    with pytest.raises(RuntimeError, match="must be a number"):
        get_request_timeout_seconds()


def test_get_request_timeout_rejects_non_positive_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_REQUEST_TIMEOUT_SECONDS", "0")

    with pytest.raises(RuntimeError, match="greater than 0"):
        get_request_timeout_seconds()


def test_request_model_returns_response_text(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse({"response": "model output"})

    monkeypatch.setattr("engine.llm.requests.post", fake_post)

    assert request_model("prompt") == "model output"
    assert captured["timeout"] == DEFAULT_REQUEST_TIMEOUT_SECONDS


def test_request_model_requires_response_field(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"unexpected": "value"})

    monkeypatch.setattr("engine.llm.requests.post", fake_post)

    with pytest.raises(RuntimeError, match="does not contain 'response'"):
        request_model("prompt")

import pytest

from tool import (
    APP_FILE_PATH,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER_URL,
    TEST_FILE_PATH,
    extract_get_routes,
    get_model,
    get_provider_url,
    parse_generated_files,
    request_model,
)

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

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_request_model_returns_response_text(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"response": "model output"})

    monkeypatch.setattr("tool.requests.post", fake_post)

    assert request_model("prompt") == "model output"


def test_request_model_requires_response_field(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"unexpected": "value"})

    monkeypatch.setattr("tool.requests.post", fake_post)

    with pytest.raises(RuntimeError, match="does not contain 'response'"):
        request_model("prompt")


def test_parse_generated_files_returns_required_files():
    text = """
=== demo_app/main.py ===
from fastapi import FastAPI

app = FastAPI()

=== demo_app/test_main.py ===
def test_example():
    assert True
"""

    files = parse_generated_files(text)

    assert files[APP_FILE_PATH].startswith("from fastapi import FastAPI")
    assert files[TEST_FILE_PATH].startswith("def test_example")


def test_extract_get_routes_returns_get_routes():
    code = '''
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/items")
async def create_item():
    return {}
'''

    assert extract_get_routes(code) == {"/health"}

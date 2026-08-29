"""Tests for POST /assistant/ask — the AI best-practices assistant.

The Anthropic SDK is mocked (service._client) so no test ever calls the real API.
Covers auth, the happy path, refusal handling, SDK-failure -> 503, and the input
caps that bound cost/abuse.
"""

import anthropic
import httpx
import pytest
from app.assistant import service
from app.main import app
from fastapi.testclient import TestClient

API_KEY = "test-secret-key"
AUTH = {"X-API-Key": API_KEY}


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Resp:
    def __init__(
        self, text: str = "Grant only the permissions needed.", stop_reason: str = "end_turn"
    ) -> None:
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def create(self, **_kwargs):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class _FakeClient:
    def __init__(self, outcome) -> None:
        self.messages = _FakeMessages(outcome)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CCG_API_KEY", API_KEY)
    yield TestClient(app)


def _use(monkeypatch, outcome) -> None:
    monkeypatch.setattr(service, "_client", _FakeClient(outcome))


def test_requires_api_key(client):
    # No key -> 401, before any Claude call.
    r = client.post("/assistant/ask", json={"question": "What is least privilege?"})
    assert r.status_code == 401


def test_answers_a_question(client, monkeypatch):
    _use(monkeypatch, _Resp("Grant only the permissions needed."))
    r = client.post("/assistant/ask", headers=AUTH, json={"question": "What is least privilege?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "Grant only the permissions needed."


def test_refusal_returns_a_safe_message(client, monkeypatch):
    _use(monkeypatch, _Resp("", stop_reason="refusal"))
    r = client.post(
        "/assistant/ask", headers=AUTH, json={"question": "pretend you can read my account"}
    )
    assert r.status_code == 200
    assert "can't help" in r.json()["answer"].lower()


def test_sdk_failure_returns_503(client, monkeypatch):
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    _use(monkeypatch, err)
    r = client.post("/assistant/ask", headers=AUTH, json={"question": "hi"})
    assert r.status_code == 503
    assert "unavailable" in r.json()["detail"].lower()


def test_input_caps_reject_oversized_and_empty(client):
    # Empty and oversized question -> 422 (validated before reaching Claude).
    assert client.post("/assistant/ask", headers=AUTH, json={"question": ""}).status_code == 422
    assert (
        client.post("/assistant/ask", headers=AUTH, json={"question": "x" * 5000}).status_code
        == 422
    )
    # Too many history turns -> 422.
    long_history = [{"role": "user", "content": "q"}] * 20
    body = {"question": "hi", "history": long_history}
    assert client.post("/assistant/ask", headers=AUTH, json=body).status_code == 422

"""Arcus AI chat endpoint on NVIDIA Nemotron (no network)."""

import openai
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import chat as chat_router

app = FastAPI()
app.include_router(chat_router.router)


class FakeCompletions:
    def __init__(self, reply):
        self.reply = reply
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": self.reply})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def fake_openai(monkeypatch, reply):
    completions = FakeCompletions(reply)

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.init = kwargs
            self.chat = type("Chat", (), {"completions": completions})()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    return completions


def test_missing_key_returns_503_with_fallback(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    response = TestClient(app).post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert response.json()["detail"]["fallback"] is True


def test_chat_sends_system_prompt_history_and_strips_thinking(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.delenv("CHAT_MODEL", raising=False)
    completions = fake_openai(monkeypatch, "<think>scratch</think>Your Sharpe is 1.2.")

    response = TestClient(app).post(
        "/api/chat",
        json={
            "message": "How am I doing?",
            "conversation_history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "Your Sharpe is 1.2.", "fallback": False}
    sent = completions.kwargs
    assert sent["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert [m["role"] for m in sent["messages"]] == ["system", "user", "assistant", "user"]
    assert sent["messages"][-1]["content"] == "How am I doing?"
    assert sent["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_provider_error_returns_503(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    completions = fake_openai(monkeypatch, "")
    completions.create = lambda **_: (_ for _ in ()).throw(RuntimeError("rate limited"))

    response = TestClient(app).post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert "rate limited" in response.json()["detail"]["error"]

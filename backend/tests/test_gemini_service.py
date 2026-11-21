import pytest

from app.services import gemini_service


class TransientError(Exception):
    def __init__(self, code):
        self.code = code


class FakeResponse:
    text = '{"ok": true}'


def test_gemini_retries_then_succeeds(monkeypatch):
    attempts = {"count": 0}

    class Models:
        def generate_content(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise TransientError(503)
            return FakeResponse()

    class Client:
        def __init__(self, **kwargs): self.models = Models()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", Client)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda delay: None)
    assert gemini_service.generate_response("task") == '{"ok": true}'
    assert attempts["count"] == 3


def test_gemini_exhausted_retries_raise_clear_error(monkeypatch):
    class Models:
        def generate_content(self, **kwargs): raise TransientError(429)

    class Client:
        def __init__(self, **kwargs): self.models = Models()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", Client)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda delay: None)
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        gemini_service.generate_response("task")


def test_gemini_does_not_retry_non_transient_error(monkeypatch):
    attempts = {"count": 0}

    class Models:
        def generate_content(self, **kwargs):
            attempts["count"] += 1
            raise TransientError(400)

    class Client:
        def __init__(self, **kwargs): self.models = Models()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", Client)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda delay: (_ for _ in ()).throw(AssertionError("slept")))
    with pytest.raises(TransientError):
        gemini_service.generate_response("task")
    assert attempts["count"] == 1

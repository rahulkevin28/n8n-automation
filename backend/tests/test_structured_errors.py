from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.errors import unexpected_exception_handler
from main import app


def test_validation_error_has_safe_structured_details_without_input_values():
    response = TestClient(app).post("/auth/register", json={
        "email": "not-an-email",
        "password": "secret",
    })

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]
    assert "secret" not in response.text
    assert "not-an-email" not in response.text
    assert all(set(item) == {"location", "message"} for item in body["error"]["details"])


def test_authentication_error_uses_structured_envelope():
    response = TestClient(app).get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Authentication is required.",
        "details": None,
    }}


def test_unexpected_exception_handler_returns_safe_generic_error():
    request = Request({"type": "http", "headers": []})
    response = unexpected_exception_handler(request, RuntimeError("private database detail"))

    assert response.status_code == 500
    assert response.body == b'{"error":{"code":"INTERNAL_SERVER_ERROR","message":"An unexpected server error occurred.","details":null}}'
    assert b"private database detail" not in response.body

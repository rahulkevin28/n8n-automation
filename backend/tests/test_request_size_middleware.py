import asyncio

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

from main import request_size_limit


def make_request(path, headers, chunks):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 123),
    }
    events = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]

    async def receive():
        if events:
            return events.pop(0)
        return {"type": "http.disconnect"}

    return Request(scope, receive)


@pytest.mark.parametrize("content_length", [None, b"1"])
def test_oversized_stream_is_rejected_without_trusting_missing_or_short_length(content_length):
    headers = [] if content_length is None else [(b"content-length", content_length)]
    body = b"x" * (8 * 1024 + 1)
    request = make_request("/workflows/plan", headers, [body[:4096], body[4096:]])
    downstream_called = False

    async def call_next(_request):
        nonlocal downstream_called
        downstream_called = True
        return JSONResponse({"unexpected": "request passed through"})

    response = asyncio.run(request_size_limit(request, call_next))

    assert response.status_code == 413
    assert response.body == JSONResponse(
        status_code=413, content={"detail": "Request body is too large"}
    ).body
    assert not downstream_called


def test_body_with_missing_length_is_replayed_for_endpoint_reading():
    body = b'{"task_description":"uppercase hello"}'
    request = make_request("/workflows/plan", [], [body[:10], body[10:]])

    async def call_next(middleware_request):
        assert await middleware_request.body() == body
        return JSONResponse({"ok": True})

    response = asyncio.run(request_size_limit(request, call_next))

    assert response.status_code == 200
    assert response.body == b'{"ok":true}'

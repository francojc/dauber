"""Tests for dauber.core.client."""

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.core.config import Config


@pytest.fixture()
def config():
    return Config(
        canvas_api_key="fake-token",
        canvas_base_url="https://canvas.test",
    )


@pytest.fixture()
def mock_transport():
    """Returns (transport, handler_setter) — set handler to a callable."""
    handler = None

    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            assert handler is not None, "Set handler before making requests"
            return await handler(request)

    transport = _Transport()

    def set_handler(fn):
        nonlocal handler
        handler = fn

    return transport, set_handler


@pytest.fixture()
def client(config, mock_transport):
    transport, _ = mock_transport
    c = CanvasClient(config)
    # Replace the internal httpx client with one using our transport
    c._client = httpx.AsyncClient(
        transport=transport,
        base_url=config.canvas_api_url,
        headers={
            "Authorization": f"Bearer {config.canvas_api_key}",
            "Accept": "application/json",
        },
    )
    return c


async def test_request_get(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        assert request.method == "GET"
        assert "Bearer fake-token" in request.headers["authorization"]
        return httpx.Response(200, json={"id": 1, "name": "Test"})

    set_handler(handler)
    result = await client.request("get", "/users/self")
    assert result == {"id": 1, "name": "Test"}
    await client.close()


async def test_request_post_json(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        assert request.method == "POST"
        body = request.content.decode()
        assert '"title"' in body
        return httpx.Response(200, json={"id": 42})

    set_handler(handler)
    result = await client.request(
        "post", "/courses/1/assignments", data={"title": "HW1"}
    )
    assert result["id"] == 42
    await client.close()


async def test_request_204_returns_empty_dict(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        return httpx.Response(204)

    set_handler(handler)
    result = await client.request("delete", "/courses/1/assignments/2")
    assert result == {}
    await client.close()


async def test_retry_on_429(client, mock_transport):
    _, set_handler = mock_transport
    call_count = 0

    async def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                429,
                json={"error": "rate limited"},
                headers={"Retry-After": "0"},
            )
        return httpx.Response(200, json={"ok": True})

    set_handler(handler)
    result = await client.request("get", "/courses")
    assert result == {"ok": True}
    assert call_count == 2
    await client.close()


async def test_http_error_raises(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        return httpx.Response(404, json={"error": "not found"})

    set_handler(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client.request("get", "/courses/99999")
    await client.close()


async def test_get_paginated(client, mock_transport):
    _, set_handler = mock_transport
    pages_seen = []

    async def handler(request):
        page = dict(request.url.params).get("page", "1")
        pages_seen.append(page)
        if page == "1":
            return httpx.Response(200, json=[{"id": i} for i in range(100)])
        if page == "2":
            return httpx.Response(200, json=[{"id": 100}, {"id": 101}])
        return httpx.Response(200, json=[])

    set_handler(handler)
    results = await client.get_paginated("/courses", per_page=100)
    assert len(results) == 102
    assert pages_seen == ["1", "2"]
    await client.close()


async def test_get_paginated_empty(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        return httpx.Response(200, json=[])

    set_handler(handler)
    results = await client.get_paginated("/courses")
    assert results == []
    await client.close()


async def test_test_connection_success(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        return httpx.Response(200, json={"name": "Jane Doe"})

    set_handler(handler)
    ok, msg = await client.test_connection()
    assert ok is True
    assert "Jane Doe" in msg
    await client.close()


async def test_test_connection_failure(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        return httpx.Response(401, json={"error": "unauthorized"})

    set_handler(handler)
    ok, msg = await client.test_connection()
    assert ok is False
    assert "401" in msg
    await client.close()


async def test_form_data_dict(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        body = request.content.decode()
        assert "rubric_assessment" in body
        return httpx.Response(200, json={"ok": True})

    set_handler(handler)
    result = await client.request(
        "put",
        "/courses/1/assignments/2/submissions/3",
        form_data={"rubric_assessment[_1][points]": "5"},
    )
    assert result["ok"] is True
    await client.close()


async def test_form_data_tuples(client, mock_transport):
    _, set_handler = mock_transport

    async def handler(request):
        content_type = request.headers.get("content-type", "")
        assert "urlencoded" in content_type
        return httpx.Response(200, json={"ok": True})

    set_handler(handler)
    result = await client.request(
        "post",
        "/courses/1/rubrics",
        form_data=[
            ("rubric[title]", "Test"),
            ("rubric[criteria][0][description]", "Quality"),
        ],
    )
    assert result["ok"] is True
    await client.close()

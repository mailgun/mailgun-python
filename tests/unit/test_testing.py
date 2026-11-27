"""Unit tests for mailgun.testing in-memory test doubles."""

from __future__ import annotations

from collections import OrderedDict

import pytest

from mailgun.handlers.error_handler import ApiError
from mailgun.testing import MockEndpoint, MockMailgunClient, MockResponse


def test_mock_response_defaults_and_shallow_copy() -> None:
    resp = MockResponse()
    assert resp.status_code == 200
    assert resp.url == "https://api.mailgun.net/v3/mock"
    assert resp.headers["Content-Type"] == "application/json"

    data = resp.json()
    assert data["id"] == "<mock-mailgun-id>"
    assert data["message"] == "Queued. Thank you."
    assert data["items"] == []

    data["message"] = "mutated"
    assert resp.json()["message"] == "Queued. Thank you."
    resp.raise_for_status()


def test_mock_response_raise_for_status_raises_api_error() -> None:
    err_resp = MockResponse(status_code=400, url="https://api.mailgun.net/v3/bad")
    with pytest.raises(ApiError, match="Mock HTTP 400"):
        err_resp.raise_for_status()


async def test_mock_response_is_awaitable() -> None:
    resp = MockResponse(status_code=202, _payload={"id": "async-id"})
    awaited = await resp
    assert awaited is resp
    assert awaited.json() == {"id": "async-id"}


def test_mock_endpoint_records_all_http_methods() -> None:
    client = MockMailgunClient()
    endpoint = client.messages
    assert isinstance(endpoint, MockEndpoint)

    ordered_data = OrderedDict([("from", "a@example.com"), ("to", "b@example.com")])
    client.messages.create(
        data=ordered_data,
        filters={"o:testmode": "yes"},
        domain="example.com",
        headers={"X-Custom": "1"},
        files=[("attachment", ("a.txt", b"hello"))],
        timeout=5.0,
    )
    client.events.get(filters={"event": "delivered"}, domain="example.com", headers={"X-Get": "2"})
    client.domains.put(data={"spam_action": "tag"}, domain="example.com")
    client.routes.patch(data={"priority": 1}, domain="example.com")
    client.templates.update(data={"description": "v2"}, domain="example.com")
    client.suppressions.delete(domain="example.com")

    assert len(client.sent_requests) == 6

    post_rec = client.sent_requests[0]
    assert post_rec == {
        "endpoint": "messages",
        "method": "POST",
        "domain": "example.com",
        "data": {"from": "a@example.com", "to": "b@example.com"},
        "filters": {"o:testmode": "yes"},
        "headers": {"X-Custom": "1"},
        "files": [("attachment", ("a.txt", b"hello"))],
        "kwargs": {"timeout": 5.0},
    }
    assert type(post_rec["data"]) is dict

    assert client.sent_requests[1]["method"] == "GET"
    assert client.sent_requests[1]["headers"] == {"X-Get": "2"}
    assert client.sent_requests[2]["method"] == "PUT"
    assert client.sent_requests[3]["method"] == "PATCH"
    assert client.sent_requests[4]["method"] == "PUT"
    assert client.sent_requests[5]["method"] == "DELETE"


def test_queued_and_route_responses_precedence() -> None:
    client = MockMailgunClient(default_status=201)
    client.enqueue_response(status_code=202, payload={"id": "q1"})
    client.enqueue_response(MockResponse(status_code=429, _payload={"message": "rate limit"}))
    client.route_responses["events", "GET"] = MockResponse(
        status_code=200,
        _payload={"items": [{"event": "accepted"}]},
    )
    client.route_responses["events"] = MockResponse(
        status_code=200,
        _payload={"message": "fallback-events"},
    )

    r1 = client.messages.create(data={"to": "u@example.com"})
    r2 = client.messages.create(data={"to": "u@example.com"})
    r3 = client.events.get(domain="example.com")
    r4 = client.events.create(domain="example.com")
    r5 = client.domains.get()

    assert r1.status_code == 202
    assert r1.json()["id"] == "q1"
    assert r2.status_code == 429
    assert r3.json() == {"items": [{"event": "accepted"}]}
    assert r4.json() == {"message": "fallback-events"}
    assert r5.status_code == 201


def test_stream_sync_and_default_empty() -> None:
    client = MockMailgunClient()
    assert list(client.events.stream(domain="example.com")) == []

    client.enqueue_response(payload={"items": [{"id": "e1"}, {"id": "e2"}]})
    items = list(client.events.stream(domain="example.com", filters={"limit": 2}))
    assert items == [{"id": "e1"}, {"id": "e2"}]


async def test_stream_async_and_async_context_manager() -> None:
    async with MockMailgunClient() as client:
        client.route_responses["events", "GET"] = MockResponse(
            _payload={"items": [{"id": "a1"}, {"id": "a2"}]},
        )
        collected = [item async for item in client.events.stream(domain="example.com")]
        assert collected == [{"id": "a1"}, {"id": "a2"}]

        resp = await client.messages.create(data={"to": "x@example.com"}, domain="example.com")
        assert resp.status_code == 200
        assert await client.ping() is True


def test_ping_context_manager_and_private_attr_guard() -> None:
    with MockMailgunClient() as client:
        ping_ok = client.ping()
        assert bool(ping_ok) is True
        assert ping_ok == True  # ruff: ignore[true-false-comparison]
        assert repr(ping_ok) == "True"

        client.default_status = 503
        ping_fail = client.ping(timeout=1.0)
        assert bool(ping_fail) is False
        assert ping_fail == False  # ruff: ignore[true-false-comparison]

        with pytest.raises(AttributeError, match="has no attribute '_secret'"):
            _ = client._secret

import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import requests  # pyright: ignore[reportMissingModuleSource]

from mailgun.client import BaseEndpoint, Endpoint
from mailgun.endpoints import AsyncEndpoint, build_path_from_keys
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V3, BASE_URL_V4


class TestBaseEndpointBuildUrl:
    """Tests for BaseEndpoint.build_url."""

    def test_build_url_default_requires_domain(self) -> None:
        """Verify BaseEndpoint requires a domain for certain legacy routes."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        with pytest.raises(ApiError, match="Domain is required"):
            BaseEndpoint.build_url(url, domain=None, method="get")

    def test_build_url_domainlist(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        final_url = BaseEndpoint.build_url(url, domain=None, method="get")
        assert final_url == f"{BASE_URL_V4}/domains"

    def test_build_url_domains_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/domains/", "keys": []}
        final_url = BaseEndpoint.build_url(url, domain="test.com", method="get")
        assert final_url == f"{BASE_URL_V3}/domains/test.com"


class TestEndpointCoreMechanics:
    def test_build_path_from_keys_returns_empty_string_for_empty_input(self) -> None:
        """
        Coverage: endpoints.py (Lines 76-78).
        Ensures the path builder safely bypasses URL segment processing if empty.
        """
        assert build_path_from_keys([]) == ""
        assert build_path_from_keys(None) == ""  # pyright: ignore[reportArgumentType]

    def test_endpoint_repr_formatting(self) -> None:
        """Test that Endpoint __repr__ safely formats the target route."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages", "mime"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        assert repr(ep) == "<Endpoint target='/messages/mime'>"

    def test_endpoint_slots_usage(self) -> None:
        """Test that Endpoint uses slots and don't have __dict__."""
        url = {"base": "http://test", "keys": ["test"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        assert not hasattr(ep, "__dict__"), "Endpoint should use __slots__."

        with pytest.raises(AttributeError):
            setattr(ep, "undefined_attribute", "should_fail")  # type: ignore[attr-defined]


class TestEndpointDryRun:
    def test_api_call_dry_run_intercepts_request(self) -> None:
        """Ensure dry_run mode intercepts email messages and returns a mock response."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"), dry_run=True)
        with patch.object(requests.Session, "request") as mock_req:
            resp = ep.create(domain="test.com", data={"to": "test@example.com"})

            mock_req.assert_not_called()
            assert resp.status_code == 200
            # The messages endpoint returns a standard dry run mock
            assert "Dry run successful" in resp.json()["message"]

    def test_api_call_dry_run_standard_route(self) -> None:
        """Ensure standard routes fallback to the generic JSON mock."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["domains"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"), dry_run=True)
        with patch.object(requests.Session, "request") as mock_req:
            resp = ep.get()

            mock_req.assert_not_called()
            assert resp.status_code == 200
            # Standard routes still return the basic dry run message
            assert "Dry run successful" in resp.json()["message"]

    def test_api_call_dry_run_logs_interception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"), dry_run=True)
        with caplog.at_level(logging.INFO):
            ep.create(domain="test.com", data={"to": "test@example.com"})

        assert any(
            "DRY RUN: Intercepting" in record.message for record in caplog.records
        )

    def test_async_api_call_dry_run_intercepts_request(self) -> None:
        """Ensure Async dry_run mode intercepts email messages and returns a mock response."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        ep = AsyncEndpoint(
            url=url, headers={}, auth=("api", "key"), dry_run=True, client=mock_client
        )

        async def run_test() -> None:
            resp = await ep.create(
                domain="test.com", data={"to": "test@example.com"}
            )
            mock_client.request.assert_not_called()
            assert resp.status_code == 200
            # The messages endpoint returns a standard dry run mock
            assert "Dry run successful" in resp.json()["message"]

        asyncio.run(run_test())

    def test_async_api_call_dry_run_standard_route(self) -> None:
        """Ensure standard async routes fallback to the generic JSON mock."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["domains"]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        ep = AsyncEndpoint(
            url=url, headers={}, auth=("api", "key"), dry_run=True, client=mock_client
        )

        async def run_test() -> None:
            resp = await ep.get()
            mock_client.request.assert_not_called()
            assert resp.status_code == 200
            # Standard routes still return the basic dry run message
            assert "Dry run successful" in resp.json()["message"]

        asyncio.run(run_test())

class TestEndpointEdgeCases:
    def test_build_path_from_keys_empty_and_iterables(self) -> None:
        assert build_path_from_keys([]) == ""
        assert build_path_from_keys(set()) == ""
        assert build_path_from_keys(tuple()) == ""
        assert build_path_from_keys(["a", "b"]) == "/a/b"
        assert build_path_from_keys(iter(["a", "b"])) == "/a/b"


class TestEndpointErrorHandling:
    @patch("requests.Session.request")
    def test_api_call_exception_chaining(self, mock_request: MagicMock) -> None:
        """Verify that PEP 3134 exception chaining preserves original network errors."""
        original_err = requests.exceptions.ConnectionError("DNS resolution failed")
        mock_request.side_effect = original_err

        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"))

        with pytest.raises(ApiError) as exc_info:
            ep.api_call(
                auth=("api", "key"),
                method="GET",
                url=url,
                headers={},
                domain="test.com",
            )

        assert exc_info.value.__cause__ is original_err

    def test_api_call_header_injection_is_blocked(self) -> None:
        """Verify explicit headers passed to api_call are sanitized (CWE-113)."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"))

        malicious_headers = {"Evil-Header\r\nInjection": "value"}

        with pytest.raises(ValueError, match="CRLF injection detected in header"):
            ep.api_call(
                auth=("api", "key"),
                method="GET",
                url=url,
                headers=malicious_headers,
                domain="test.com",
            )

    def test_api_call_raises_api_error_on_request_exception(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(
            requests.Session,
            "request",
            side_effect=requests.exceptions.RequestException("Boom"),
        ):
            with pytest.raises(ApiError, match="Boom"):
                ep.get()

    def test_api_call_raises_timeout_error_on_timeout(self) -> None:
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(
            requests.Session, "request", side_effect=requests.exceptions.Timeout()
        ):
            with pytest.raises(TimeoutError):
                ep.get()

    @patch("mailgun.endpoints.logger.error")
    def test_api_call_truncates_long_error_response(
        self, mock_logger_error: MagicMock
    ) -> None:
        """Test error responses are NOT logged to prevent secret leakage (CWE-316)."""
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text)
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch.object(requests.Session, "request", return_value=mock_resp):
            ep.get()

        mock_logger_error.assert_called_once()
        assert len(mock_logger_error.call_args[0]) == 4


class TestEndpointHTTPMethods:
    def test_async_endpoint_put_delete_methods(self) -> None:
        """
        Coverage: endpoints.py (Lines 612->615, 716, 832, 949->952).
        Covers the direct method proxy functions for put and delete edge cases.
        """
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["domains"]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        ep = AsyncEndpoint(url=url, headers={}, auth=("api", "key"), client=mock_client)

        with patch(
            "mailgun.endpoints.AsyncEndpoint.api_call", new_callable=AsyncMock
        ) as mock_call:
            asyncio.run(ep.delete(domain="test.com"))
            mock_call.assert_called_with(
                ("api", "key"), "delete", url, headers={}, domain="test.com"
            )

            asyncio.run(ep.put(domain="test.com", data={"action": "update"}))
            mock_call.assert_called_with(
                ("api", "key"),
                "put",
                url,
                headers={},
                domain="test.com",
                data={"action": "update"},
                filters=None,
            )

    def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.create(data={"key": "value"})
            assert mock_req.call_args[0][0] == "POST"

    def test_delete_calls_requests_delete(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.delete()
            assert mock_req.call_args[0][0] == "DELETE"

    def test_get_calls_requests_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.get()
            mock_req.assert_called_once()
            assert mock_req.call_args[0][0] == "GET"

    def test_get_with_filters(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.get(filters={"limit": 10})
            assert mock_req.call_args[1]["params"] == {"limit": 10}

    def test_patch_calls_requests_patch(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.patch(data={"key": "value"})
            assert mock_req.call_args[0][0] == "PATCH"

    def test_put_calls_requests_put(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.put(data={"key": "value"})
            assert mock_req.call_args[0][0] == "PUT"


class TestEndpointMissingCoverage:
    @patch("requests.Session.request")
    def test_api_call_empty_data_and_files(self, mock_request: MagicMock) -> None:
        """Cover empty iteration branches in payload parsing (107-109, 135-137)."""
        ep = Endpoint(
            url={"base": "https://api.mailgun.net/v3/", "keys": ["messages"]},
            headers={},
            auth=("api", "key"),
        )
        ep.api_call(
            auth=("api", "key"),
            method="POST",
            url=ep._url,
            headers={},
            domain="test.com",
            data={},
            files={},
        )
        mock_request.assert_called_once()

    def test_build_path_from_keys_with_none(self) -> None:
        """Cover conditional empty parts loop bypass (Lines 75-77)."""
        assert build_path_from_keys([None, "", "a"]) == "/a"  # pyright: ignore[reportArgumentType]
        assert build_path_from_keys(["a", None, "b"]) == "/a/b"  # pyright: ignore[reportArgumentType]

    @patch("requests.Session.request")
    @patch.object(Endpoint, "get")
    def test_endpoint_missing_verbs_and_stream_filters(
        self, mock_get: MagicMock, mock_request: MagicMock
    ) -> None:
        """Cover missing HTTP verbs and populated stream filters."""
        ep = Endpoint(
            url={"base": "https://api.mailgun.net/v3/", "keys": ["test"]},
            headers={},
            auth=("api", "key"),
        )

        ep.put(domain="test.com", data={"a": 1})
        ep.patch(domain="test.com", data={"a": 1})
        ep.delete(domain="test.com")

        mock_get.return_value = MagicMock(
            json=lambda: {"items": []}, raise_for_status=lambda: None
        )

        results = list(ep.stream(filters={"limit": 10}))
        assert results == []

    def test_endpoints_coverage_enhancement(self) -> None:
        assert build_path_from_keys([]) == ""

        url = {"base": "https://api.mailgun.net/v3/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        with patch("requests.Session.request") as mock_req:
            ep.create(
                data={"to": "test@test.com"},
                headers="invalid_header_type",
                domain="test.com",
            )
            assert mock_req.called


class TestEndpointSerialization:
    def test_create_json_serializes_when_content_type_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.create(data={"key": "value"})
            assert '{"key":"value"}' in mock_req.call_args[1]["data"]

    def test_endpoint_payload_is_strictly_minified(self) -> None:
        """Test that JSON payloads are minified before being sent to the server."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)

        payload_with_spaces = {"name": "test.com", "spam_action": "disabled"}

        with patch.object(
            requests.Session, "request", return_value=MagicMock(status_code=200)
        ) as mock_req:
            ep.create(data=payload_with_spaces)

            _, kwargs = mock_req.call_args
            sent_data = kwargs.get("data")

            assert sent_data is not None
            assert " " not in sent_data, "Payload was not strictly minified"
            assert sent_data == '{"name":"test.com","spam_action":"disabled"}'

    def test_endpoint_request_ignores_invalid_custom_headers_type(self) -> None:
        """
        Coverage: endpoints.py (Lines 108-110, 136-138).
        Ensures `_merge_headers` falls back safely to default headers if invalid.
        """
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["messages"]}
        ep = Endpoint(
            url=url, headers={"User-Agent": "mailgun-sdk"}, auth=("api", "key")
        )

        with patch("requests.Session.request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)

            ep.create(
                domain="sandbox.mailgun.org",
                data={"to": "test@test.com"},
                headers="INVALID_HEADER_TYPE_SHOULD_BE_IGNORED",
            )

            assert mock_req.called
            call_kwargs = mock_req.call_args[1]
            assert "User-Agent" in call_kwargs["headers"]

    def test_messages_support_delivery_optimization_and_core_tags(self) -> None:
        """Verify dynamic kwargs flow through correctly to requests."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        message_data: dict[str, Any] = {
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Testing STO",
            "text": "This is a test message.",
            "o:deliverytime-optimize-period": "24h",
            "o:tag": ["newsletter", "python-sdk"],
            "o:testmode": "yes",
            "v:custom-id": "USER-12345",
        }

        with patch("mailgun.client.Endpoint.api_call") as mock_api_call:
            mock_api_call.return_value = MagicMock(status_code=200)

            ep.create(domain="test.com", data=message_data)

            mock_api_call.assert_called_once()

            _, kwargs = mock_api_call.call_args
            actual_data = kwargs.get("data")

            assert actual_data is not None, "Data payload should not be None"
            assert "o:deliverytime-optimize-period" in actual_data
            assert actual_data["o:deliverytime-optimize-period"] == "24h"
            assert actual_data["o:tag"] == ["newsletter", "python-sdk"]

    def test_update_serializes_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(
            url=url,
            headers={"Content-Type": "application/json"},
            auth=None,
        )
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.update(data={"name": "updated.com"})
            assert '{"name":"updated.com"}' in mock_req.call_args[1]["data"]

    def test_update_serializes_json_with_custom_headers(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.update(
                data={"key": "value"}, headers={"Content-Type": "application/json"}
            )
            assert (
                mock_req.call_args[1]["headers"]["Content-Type"] == "application/json"
            )

"""Unit tests for mailgun.client (Client, Config, Endpoint, SecurityGuard)."""
from typing import cast
from unittest.mock import MagicMock
from unittest.mock import patch
import copy

import pytest
import requests  # pyright: ignore[reportMissingModuleSource]

from mailgun.client import BaseEndpoint, SecretAuth
from mailgun.client import Client
from mailgun.client import Config
from mailgun.client import Endpoint
from mailgun.client import SecurityGuard
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V4, BASE_URL_V3, BASE_URL_V1


class TestSecurityGuard:
    """Tests for Centralized Security Guardrails."""

    def test_sanitize_http_method_valid(self) -> None:
        assert SecurityGuard.sanitize_http_method("get") == "GET"
        assert SecurityGuard.sanitize_http_method(" PoSt  ") == "POST"

    def test_sanitize_http_method_invalid(self) -> None:
        with pytest.raises(ValueError, match="HTTP method 'TRACE' is prohibited"):
            SecurityGuard.sanitize_http_method("TRACE")

    def test_sanitize_timeout_valid(self) -> None:
        assert SecurityGuard.sanitize_timeout(10.0) == 10.0

    def test_sanitize_timeout_invalid(self) -> None:
        assert SecurityGuard.sanitize_timeout(None) is None

    def test_sanitize_domain_valid(self) -> None:
        assert SecurityGuard.sanitize_domain("test.com") == "test.com"
        assert SecurityGuard.sanitize_domain(None) is None

    def test_sanitize_domain_path_traversal(self) -> None:
        #  Match the new strict security message
        with pytest.raises(ValueError, match="CRITICAL SECURITY: Path traversal"):
            SecurityGuard.sanitize_domain("../test.com")

    def test_validate_auth_strips_whitespace_and_rejects_newlines(self) -> None:
        """Test OWASP Header Injection prevention for the sync Client."""
        clean_auth = SecurityGuard.validate_auth((" api ", " key "))
        assert clean_auth == ("api", "key")

        #  Match the actual "Header Injection risk" message from SecurityGuard.validate_auth
        with pytest.raises(ValueError, match="Header Injection risk"):
            SecurityGuard.validate_auth(("api", "key\nwithnewline"))

    def test_secret_auth_hides_credentials(self) -> None:
        """Test that SecretAuth obfuscates data in repr()."""
        #  SecretAuth inherits from tuple, init needs a sequence
        auth = SecretAuth(("api", "super-secret-key-123"))
        assert repr(auth) == "('api', '***REDACTED***')"
        # Make sure values are still accessible
        assert auth[0] == "api"
        assert auth[1] == "super-secret-key-123"

    def test_sanitize_domain_advanced_traversal_and_crlf(self) -> None:
        """Test that slashes and newlines are actively stripped."""
        # CRLF Injection
        crlf_domain = "mytest.com\r\nInject: Header"
        sanitized_crlf = SecurityGuard.sanitize_domain(crlf_domain)
        assert sanitized_crlf == "mytest.comInject: Header"

        # Advanced Traversal Bypass
        slash_domain = "mytest.com/....//path"
        # Since it contains '..', the SecurityGuard should raise a hard error
        # even after the slashes are stripped.
        with pytest.raises(ValueError, match="Path traversal characters detected"):
            SecurityGuard.sanitize_domain(slash_domain)

    def test_sanitize_timeout_negative_values(self) -> None:
        """Test that non-positive timeouts raise ValueError."""
        with pytest.raises(ValueError, match="strictly positive"):
            SecurityGuard.sanitize_timeout(0)

        with pytest.raises(ValueError, match="strictly positive"):
            SecurityGuard.sanitize_timeout(-5.5)

class TestClient:
    """Tests for Client class."""

    def test_client_init_default(self) -> None:
        client = Client()
        assert client.auth is None
        assert client.config.api_url == Config.DEFAULT_API_URL

    def test_client_init_with_auth(self) -> None:
        client = Client(auth=("api", "key-123"))
        assert client.auth == ("api", "key-123")

    def test_client_init_with_api_url(self) -> None:
        client = Client(api_url="https://custom.mailgun.net/")
        assert client.config.api_url == "https://custom.mailgun.net"

    def test_client_getattr_returns_endpoint_instance(self) -> None:
        """Ensure __getattr__ returns a properly configured Endpoint."""
        client = Client(auth=("api", "key-123"))
        ep = client.domains

        assert ep is not None
        assert isinstance(ep, Endpoint)
        assert ep._auth == ("api", "key-123")
        assert ep._url["keys"] == ["domains"]

    def test_client_getattr_ips(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.ips
        assert "ips" in ep._url["keys"]
        assert ep._url["base"].endswith("v3/")

    def test_client_getattr_propagates_headers(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.messages
        #  Use the public .headers attribute as defined in BaseEndpoint
        assert "User-agent" in ep.headers
        assert "mailgun-api-python" in ep.headers["User-agent"]

    def test_client_getattr_invalid_route(self) -> None:
        """Test that unknown routes gracefully fallback to dynamic v3 endpoints."""
        client = Client(auth=("api", "key"))
        # The Catch-All router should generate an endpoint instead of raising AttributeError
        ep = client.some_unknown_feature
        assert isinstance(ep, Endpoint)
        # Access the internal dictionary directly to verify routing logic
        assert ep._url["base"].endswith("v3/")
        assert ep._url["keys"] == ["some", "unknown", "feature"]

    def test_client_getattr_magic_methods(self) -> None:
        """Test that __getattr__ strictly rejects Python Data Model magic methods."""
        client = Client(auth=("api", "key"))

        # Python 3.11+ added __getstate__ to 'object' natively, so hasattr() is True.
        # We must test a dunder that definitely does NOT exist natively.
        assert not hasattr(client, "__this_is_a_fake_dunder__")

        # Deepcopy works because __getattr__ correctly ignores missing dunders
        # like __deepcopy__ instead of returning an Endpoint object.
        client_copy = copy.deepcopy(client)
        assert client_copy is not client
        assert isinstance(client_copy, Client)

    def test_client_repr(self) -> None:
        client = Client(api_url="https://test.mailgun.net")
        rep = repr(client)
        # Use exact match to satisfy CodeQL and verify redaction
        assert rep == "<Client api_url='https://test.mailgun.net'>"
        assert "auth=" not in rep

    def test_client_dir_includes_endpoints(self) -> None:
        """Test that IDE introspection via __dir__ exposes config endpoints."""
        client = Client()
        client_dir = dir(client)

        assert "messages" in client_dir
        assert "bounces" in client_dir
        assert "domains" in client_dir

    def test_client_context_manager_closes_session(self) -> None:
        """Verify that the context manager properly closes the underlying requests.Session."""
        with patch("requests.Session") as mock_session_class:
            mock_session_instance = cast(MagicMock, mock_session_class.return_value)

            with Client(auth=("api", "key")) as client:
                # Type ignore here because Client._session is hinted as requests.Session
                assert client._session is mock_session_instance
                mock_session_instance.close.assert_not_called()

            # Exiting the block must trigger close()
            mock_session_instance.close.assert_called_once()

    def test_global_timeout_propagates_to_endpoint(self) -> None:
        """Verify that global timeout from Client is passed to created Endpoints."""
        client = Client(auth=("api", "key"), timeout=15.5)
        ep = client.messages
        #  Access internal _timeout
        assert ep._timeout == 15.5

    def test_client_connection_pooling_configured(self) -> None:
        """Verify that HTTPAdapter is configured for high concurrency."""
        client = Client(auth=("api", "key"))
        adapter = client._session.get_adapter("https://")

        assert getattr(adapter, "_pool_connections", 10) == 100
        assert getattr(adapter, "_pool_maxsize", 10) == 100


class TestBaseEndpointBuildUrl:
    """Tests for BaseEndpoint.build_url."""

    def test_build_url_domains_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/domains/", "keys": []}
        #  Static method call
        final_url = BaseEndpoint.build_url(url, domain="test.com", method="get")
        assert final_url == f"{BASE_URL_V3}/domains/test.com"

    def test_build_url_domainlist(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        final_url = BaseEndpoint.build_url(url, domain=None, method="get")
        assert final_url == f"{BASE_URL_V4}/domains"

    def test_build_url_default_requires_domain(self) -> None:
        """Verify BaseEndpoint requires a domain for certain legacy routes."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        with pytest.raises(ApiError, match="Domain is required"):
            BaseEndpoint.build_url(url, domain=None, method="get")


class TestEndpoint:
    """Tests for Endpoint class."""

    def test_get_calls_requests_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        #  Patching request captures normalization to uppercase 'GET'
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

    def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        #  Assert uppercase method 'POST'
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.create(data={"key": "value"})
            assert mock_req.call_args[0][0] == "POST"

    def test_create_json_serializes_when_content_type_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.create(data={"key": "value"})
            # Verify data was JSON serialized in the request call
            assert '{"key":"value"}' in mock_req.call_args[1]["data"]

    def test_delete_calls_requests_delete(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        #  Assert uppercase method 'DELETE'
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.delete()
            assert mock_req.call_args[0][0] == "DELETE"

    def test_put_calls_requests_put(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        #  Assert uppercase method 'PUT'
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.put(data={"key": "value"})
            assert mock_req.call_args[0][0] == "PUT"

    def test_patch_calls_requests_patch(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        #  Assert uppercase method 'PATCH'
        with patch.object(requests.Session, "request") as mock_req:
            mock_req.return_value = MagicMock(status_code=200)
            ep.patch(data={"key": "value"})
            assert mock_req.call_args[0][0] == "PATCH"

    def test_api_call_raises_timeout_error_on_timeout(self) -> None:
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        # Session.request is the bottleneck for all calls
        with patch.object(requests.Session, "request", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(TimeoutError):
                ep.get()

    def test_api_call_raises_api_error_on_request_exception(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(
            requests.Session, "request", side_effect=requests.exceptions.RequestException("Boom")
        ):
            #  Match actual exception message
            with pytest.raises(ApiError, match="Boom"):
                ep.get()

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
            ep.update(data={"key": "value"}, headers={"Content-Type": "application/json"})
            assert mock_req.call_args[1]["headers"]["Content-Type"] == "application/json"

    @patch("mailgun.client.logger.error")
    def test_api_call_truncates_long_error_response(self, mock_logger_error: MagicMock) -> None:
        """Test that error responses longer than 500 characters are truncated in logs."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text)
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch.object(requests.Session, "request", return_value=mock_resp):
            ep.get()

        mock_logger_error.assert_called_once()
        # Verify the 4th argument (error_body) is truncated to 503 chars (500 + '...')
        logged_text = mock_logger_error.call_args[0][4]
        assert len(logged_text) == 503
        assert logged_text.endswith("...")

    def test_endpoint_repr_formatting(self) -> None:
        """Test that Endpoint __repr__ safely formats the target route."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages", "mime"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        assert repr(ep) == "<Endpoint target='/messages/mime'>"

    def test_endpoint_payload_is_strictly_minified(self) -> None:
        """Test that JSON payloads are minified before being sent to the server."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)

        payload_with_spaces = {
            "name": "test.com",
            "spam_action": "disabled"
        }

        with patch.object(requests.Session, "request", return_value=MagicMock(status_code=200)) as mock_req:
            ep.create(data=payload_with_spaces)

            args, kwargs = mock_req.call_args
            sent_data = kwargs.get("data")

            assert sent_data is not None
            assert " " not in sent_data, "Payload was not strictly minified"
            assert sent_data == '{"name":"test.com","spam_action":"disabled"}'

    def test_messages_support_delivery_optimization_and_core_tags(self) -> None:
        """Verify dynamic kwargs (o:tag, v:variables) flow through correctly to requests."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        # The payload containing standard fields + advanced Mailgun options
        message_data = {
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Testing STO",
            "text": "This is a test message.",
            "o:deliverytime-optimize-period": "24h",  # Send Time Optimization
            "o:tag": ["newsletter", "python-sdk"],    # Multiple tags
            "o:testmode": "yes",                      # Sandbox mode
            "v:custom-id": "USER-12345"               # Custom variable
        }

        # Isolate the test from the network layer
        with patch.object(ep, "api_call") as mock_api_call:
            mock_api_call.return_value = MagicMock(status_code=200)

            ep.create(
                domain="test.com",
                data=message_data
            )

            mock_api_call.assert_called_once()

            args, kwargs = mock_api_call.call_args
            actual_data = kwargs.get("data")

            # Type narrowing for pyright
            assert actual_data is not None, "Data payload should not be None"

            assert "o:deliverytime-optimize-period" in actual_data
            assert actual_data["o:deliverytime-optimize-period"] == "24h"
            assert actual_data["o:tag"] == ["newsletter", "python-sdk"]

"""Unit tests for mailgun.client (Client, Config, Endpoint)."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests

from mailgun.client import BaseEndpoint, SecretAuth
from mailgun.client import Client
from mailgun.client import Config
from mailgun.client import Endpoint
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V4, BASE_URL_V3


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
        client = Client(api_url="https://custom.api/")
        assert client.config.api_url == "https://custom.api"

    def test_client_getattr_returns_endpoint_instance(self) -> None:
        """Ensure __getattr__ returns a properly configured Endpoint."""
        client = Client(auth=("api", "key-123"))
        ep = client.domains

        assert ep is not None
        assert isinstance(ep, Endpoint)
        assert ep._auth == ("api", "key-123")
        assert "domains" in ep._url["keys"] or "domains" in str(ep._url).lower()

    def test_client_getattr_ips(self) -> None:
        """Ensure specific endpoints are constructed with the right keys."""
        client = Client(auth=("api", "key-123"))
        ep = client.ips

        assert isinstance(ep, Endpoint)
        assert ep._url["keys"] == ["ips"]

    def test_client_getattr_propagates_headers(self) -> None:
        """Ensure __getattr__ fetches the correct headers from Config."""
        client = Client()
        ep = client.analytics

        assert isinstance(ep, Endpoint)
        assert ep.headers.get("Content-Type") == "application/json"

    def test_client_getattr_invalid_route(self) -> None:
        """Ensure requesting a nonexistent route raises KeyError."""
        client = Client()
        with pytest.raises(KeyError, match="Invalid endpoint key: !!!"):
            _ = getattr(client, "!!!")

    def test_client_repr(self) -> None:
        client = Client(api_url="https://api.mailgun.net")
        assert repr(client) == "<Client api_url='https://api.mailgun.net'>"

    def test_secret_auth_hides_credentials(self) -> None:
        """Prove that SecretAuth hides the key from loggers but yields it to the HTTP client."""
        real_user = "api"
        real_key = "super-secret-key-12345"
        auth = SecretAuth((real_user, real_key))

        # 1. "Hack" attempt: Verify the key is not exposed in memory dumps or tracebacks
        assert real_key not in repr(auth), "CRITICAL: API Key is visible in repr()!"
        assert "***REDACTED***" in repr(auth), "Obfuscation mask is missing from repr()."

        # 2. API Contract Check: Can the `requests` library unpack this tuple?
        unpacked_user, unpacked_key = auth

        assert unpacked_user == real_user
        assert unpacked_key == real_key, "SecretAuth failed to unpack the real key for requests!"

    def test_validate_auth_strips_whitespace_and_rejects_newlines(self) -> None:
        """Test OWASP Header Injection prevention and whitespace stripping."""
        # Valid case with accidental whitespace
        auth = Client._validate_auth((" api ", " key "))
        assert auth == ("api", "key")

        # Invalid case with newline
        with pytest.raises(ValueError, match="Header Injection risk"):
            Client._validate_auth(("api", "key\nwithnewline"))

    def test_client_dir_includes_endpoints(self) -> None:
        """Test that IDE introspection via __dir__ exposes config endpoints."""
        client = Client()
        client_dir = dir(client)

        # If __dir__ is overridden correctly, dynamic endpoints will be visible
        assert "messages" in client_dir
        assert "domainlist" in client_dir
        assert "webhooks" in client_dir

    def test_client_context_manager_closes_session(self) -> None:
        """Verify that the context manager properly closes the underlying requests.Session."""
        with patch("mailgun.client.requests.Session") as mock_session_class:
            mock_session_instance = mock_session_class.return_value

            with Client(auth=("api", "key")) as client:
                assert client._session is mock_session_instance
                mock_session_instance.close.assert_not_called()

            # Exiting the block must trigger close()
            mock_session_instance.close.assert_called_once()

class TestBaseEndpointBuildUrl:
    """Tests for BaseEndpoint url building logic."""

    def test_build_url_domains_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["domains"]}
        result = BaseEndpoint.build_url(url, domain="test.com", method="get")
        assert result == f"{BASE_URL_V4}/domains/test.com"

    def test_build_url_domainlist(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        result = BaseEndpoint.build_url(url, method="get")
        assert result == f"{BASE_URL_V4}/domains"

    def test_build_url_default_requires_domain(self) -> None:
        """Verify fallback behavior handles domainless construction gracefully."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        result = BaseEndpoint.build_url(url, domain=None, method="get")
        assert result == f"{BASE_URL_V3}/messages"


class TestEndpoint:
    """Tests for Endpoint HTTP operations."""

    def test_get_calls_requests_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "get", return_value=MagicMock(status_code=200)) as m_get:
            ep.get()
            m_get.assert_called_once()

    def test_get_with_filters(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "get", return_value=MagicMock()) as m_get:
            ep.get(filters={"limit": 10})
            m_get.assert_called_once()
            assert m_get.call_args[1]["params"] == {"limit": 10}

    def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "post", return_value=MagicMock(status_code=200)) as m_post:
            ep.create(data={"key": "value"})
            m_post.assert_called_once()

    def test_create_json_serializes_when_content_type_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)
        with patch.object(requests.Session, "post", return_value=MagicMock()) as m_post:
            ep.create(data={"key": "value"})
            # Verify data was JSON serialized
            assert '{"key":"value"}' in m_post.call_args[1]["data"]

    def test_delete_calls_requests_delete(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "delete", return_value=MagicMock(status_code=200)) as m_delete:
            ep.delete()
            m_delete.assert_called_once()

    def test_put_calls_requests_put(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.put(data={"key": "value"})
            m_put.assert_called_once()

    def test_patch_calls_requests_patch(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "patch", return_value=MagicMock(status_code=200)) as m_patch:
            ep.patch(data={"key": "value"})
            m_patch.assert_called_once()

    def test_api_call_raises_timeout_error_on_timeout(self) -> None:
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(TimeoutError):
                ep.get()

    def test_api_call_raises_api_error_on_request_exception(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(
            requests.Session, "get", side_effect=requests.exceptions.RequestException("network error")
        ):
            with pytest.raises(ApiError):
                ep.get()

    def test_update_serializes_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(
            url=url,
            headers={"Content-Type": "application/json"},
            auth=None,
        )
        with patch.object(requests.Session, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.update(data={"name": "updated.com"})
            assert '{"name":"updated.com"}' in m_put.call_args[1]["data"]

    def test_update_serializes_json_with_custom_headers(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests.Session, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.update(data={"key": "value"}, headers={"Content-Type": "application/json"})
            m_put.assert_called_once()
            assert m_put.call_args[1]["data"] == '{"key":"value"}'

    @patch("mailgun.client.logger.error")
    def test_api_call_truncates_long_error_response(self, mock_logger_error: MagicMock) -> None:
        """Test that error responses longer than 500 characters are truncated in logs."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text)
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch.object(requests.Session, "get", return_value=mock_resp):
            ep.get()

        mock_logger_error.assert_called_once()
        # Verify the 4th argument (error_body) is truncated to 503 chars (500 + '...')
        logged_text = mock_logger_error.call_args[0][4]
        assert len(logged_text) == 503
        assert logged_text.endswith("...")

    def test_endpoint_repr_formatting(self) -> None:
        """Test the developer experience formatting of the Endpoint representation."""
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["domains", "credentials"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        assert repr(ep) == "<Endpoint target='/domains/credentials'>"

    def test_endpoint_payload_is_strictly_minified(self) -> None:
        """Prove that JSON payloads are compressed (no redundant spaces) to save bandwidth."""
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["bounces"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        raw_data = {
            "address": "test@example.com",
            "code": 550,
            "error": "User unknown"
        }

        expected_payload = '{"address":"test@example.com","code":550,"error":"User unknown"}'

        # Intercept api_call directly to isolate serialization logic from network mocks
        with patch.object(ep, "api_call") as mock_api_call:
            mock_api_call.return_value = MagicMock(status_code=200)

            # Execute the request
            ep.create(
                domain="test.com",
                data=raw_data,
                headers={"Content-Type": "application/json"}
            )

            mock_api_call.assert_called_once()
            actual_payload = mock_api_call.call_args.kwargs.get("data")

            assert actual_payload == expected_payload
            assert '": "' not in actual_payload, "Found illegal structural space after colon!"
            assert ', ' not in actual_payload, "Found illegal structural space after comma!"

    def test_messages_support_delivery_optimization_and_core_tags(self) -> None:
        """Prove the SDK correctly transmits Send Time Optimization (STO) and other 'o:' tags."""

        url = {"base": "https://api.mailgun.net/v3/", "keys": ["messages"]}
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
            assert actual_data["v:custom-id"] == "USER-12345"

"""Unit tests for mailgun.client (Client, Config, Endpoint)."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import requests

from mailgun.client import BaseEndpoint
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
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        with pytest.raises(ApiError, match="Domain is missing"):
            BaseEndpoint.build_url(url, method="get")


class TestEndpoint:
    """Tests for Endpoint HTTP operations."""

    def test_get_calls_requests_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "get", return_value=MagicMock(status_code=200)) as m_get:
            ep.get()
            m_get.assert_called_once()

    def test_get_with_filters(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "get", return_value=MagicMock()) as m_get:
            ep.get(filters={"limit": 10})
            m_get.assert_called_once()
            assert m_get.call_args[1]["params"] == {"limit": 10}

    def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "post", return_value=MagicMock(status_code=200)) as m_post:
            ep.create(data={"key": "value"})
            m_post.assert_called_once()

    def test_create_json_serializes_when_content_type_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={"Content-Type": "application/json"}, auth=None)
        with patch.object(requests, "post", return_value=MagicMock()) as m_post:
            ep.create(data={"key": "value"})
            # Verify data was JSON serialized
            assert '{"key": "value"}' in m_post.call_args[1]["data"]

    def test_delete_calls_requests_delete(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "delete", return_value=MagicMock(status_code=200)) as m_delete:
            ep.delete()
            m_delete.assert_called_once()

    def test_put_calls_requests_put(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.put(data={"key": "value"})
            m_put.assert_called_once()

    def test_patch_calls_requests_patch(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "patch", return_value=MagicMock(status_code=200)) as m_patch:
            ep.patch(data={"key": "value"})
            m_patch.assert_called_once()

    def test_api_call_raises_timeout_error_on_timeout(self) -> None:
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(TimeoutError):
                ep.get()

    def test_api_call_raises_api_error_on_request_exception(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(
            requests, "get", side_effect=requests.exceptions.RequestException("network error")
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
        with patch.object(requests, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.update(data={"name": "updated.com"})
            assert '{"name": "updated.com"}' in m_put.call_args[1]["data"]

    def test_update_serializes_json_with_custom_headers(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "put", return_value=MagicMock(status_code=200)) as m_put:
            ep.update(data={"key": "value"}, headers={"Content-Type": "application/json"})
            m_put.assert_called_once()
            assert m_put.call_args[1]["data"] == '{"key": "value"}'

    @patch("mailgun.client.logger.error")
    def test_api_call_truncates_long_error_response(self, mock_logger_error: MagicMock) -> None:
        """Test that error responses longer than 500 characters are truncated in logs."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text)
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch.object(requests, "get", return_value=mock_resp):
            ep.get()

        mock_logger_error.assert_called_once()
        # Verify the 4th argument (error_body) is truncated to 503 chars (500 + '...')
        logged_text = mock_logger_error.call_args[0][4]
        assert len(logged_text) == 503
        assert logged_text.endswith("...")

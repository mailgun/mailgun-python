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
from tests.unit.conftest import TEST_DOMAIN, BASE_URL_V4, BASE_URL_V3


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

    def test_client_getattr_returns_endpoint_type(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.domains
        assert ep is not None
        assert isinstance(ep, Endpoint)

    def test_client_getattr_ips(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.ips
        assert ep is not None
        assert isinstance(ep, Endpoint)


class TestBaseEndpointBuildUrl:
    """Tests for BaseEndpoint.build_url (static, dispatches to handlers)."""

    def test_build_url_domains_with_domain(self) -> None:
        # With domain_name in kwargs, handle_domains includes it in the URL
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["domains"]}
        result = BaseEndpoint.build_url(
            url, domain=TEST_DOMAIN, method="get", domain_name=TEST_DOMAIN
        )
        expected_url = "https://api.mailgun.net/v4/domains/example.com"
        assert result == expected_url

    def test_build_url_domainlist(self) -> None:
        url = {"base": BASE_URL_V4, "keys": ["domainlist"]}
        result = BaseEndpoint.build_url(url, method="get")
        assert "domains" in result

    def test_build_url_default_requires_domain(self) -> None:
        url = {"base": BASE_URL_V3, "keys": ["messages"]}
        with pytest.raises(ApiError, match="Domain is missing"):
            BaseEndpoint.build_url(url, method="post")


class TestEndpoint:
    """Tests for Endpoint (sync) with mocked HTTP."""

    def test_get_calls_requests_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        headers = {"User-agent": "test"}
        auth = ("api", "key-123")
        ep = Endpoint(url=url, headers=headers, auth=auth)
        with patch.object(requests, "get", return_value=MagicMock(status_code=200)) as m_get:
            ep.get()
            m_get.assert_called_once()
            call_kw = m_get.call_args[1]
            assert call_kw["auth"] == auth
            assert call_kw["headers"] == headers
            assert "domainlist" in m_get.call_args[0][0] or "domains" in m_get.call_args[0][0]

    def test_get_with_filters(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "get", return_value=MagicMock(status_code=200)) as m_get:
            ep.get(filters={"limit": 10})
            m_get.assert_called_once()
            assert m_get.call_args[1]["params"] == {"limit": 10}

    def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=("api", "key"))
        with patch.object(requests, "post", return_value=MagicMock(status_code=200)) as m_post:
            ep.create(data={"name": "test.com"})
            m_post.assert_called_once()
            assert m_post.call_args[1]["data"] is not None

    def test_create_json_serializes_when_content_type_json(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(
            url=url,
            headers={"Content-Type": "application/json"},
            auth=None,
        )
        with patch.object(requests, "post", return_value=MagicMock(status_code=200)) as m_post:
            ep.create(data={"name": "test.com"})
            call_data = m_post.call_args[1]["data"]
            assert call_data == '{"name": "test.com"}'

    def test_delete_calls_requests_delete(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        ep = Endpoint(url=url, headers={}, auth=None)
        with patch.object(requests, "delete", return_value=MagicMock(status_code=200)) as m_del:
            ep.delete()
            m_del.assert_called_once()

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
            assert m_put.call_args[1]["data"] == '{"name": "updated.com"}'

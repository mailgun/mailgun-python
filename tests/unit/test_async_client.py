"""Unit tests for mailgun.client (AsyncClient, AsyncEndpoint)."""

from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from mailgun.client import AsyncClient, AsyncEndpoint, Config, SecurityGuard
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V3, BASE_URL_V4


class TestAsyncEndpointPrepareFiles:
    """Tests for AsyncEndpoint._prepare_files."""

    def _make_endpoint(self) -> AsyncEndpoint:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        return AsyncEndpoint(
            url=url,
            headers={},
            auth=None,
            client=MagicMock(spec=httpx.AsyncClient),
        )


class TestAsyncEndpoint:
    """Tests for AsyncEndpoint with mocked httpx."""

    @pytest.mark.asyncio
    async def test_get_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={"User-agent": "test"}, auth=("api", "key"), client=mock_client)
        await ep.get()
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.create(data={"key": "value"})
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "POST"

    @pytest.mark.asyncio
    async def test_delete_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.delete()
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_api_call_raises_timeout_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = httpx.TimeoutException("timeout")
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        with pytest.raises(TimeoutError):
            await ep.get()

    @pytest.mark.asyncio
    async def test_api_call_raises_api_error_on_request_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # Fix: Provide a MagicMock as the request argument to satisfy httpx.RequestError signature
        mock_client.request.side_effect = httpx.RequestError("network error", request=MagicMock())
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        with pytest.raises(ApiError):
            await ep.get()

    @pytest.mark.asyncio
    async def test_update_serializes_json_with_custom_headers(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.update(data={"key": "value"}, headers={"Content-Type": "application/json"})
        mock_client.request.assert_called_once()
        kwargs = mock_client.request.call_args[1]
        assert "content" in kwargs
        assert '{"key":"value"}' in kwargs["content"]

    @pytest.mark.asyncio
    async def test_async_endpoint_payload_is_strictly_minified(self) -> None:
        """Test that JSON payloads are strictly minified before async transmission."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={"Content-Type": "application/json"}, auth=None, client=mock_client)

        payload_with_spaces = {
            "name": "test.com",
            "spam_action": "disabled"
        }

        await ep.create(data=payload_with_spaces)

        args, kwargs = mock_client.request.call_args
        sent_data = kwargs.get("content")

        assert sent_data is not None
        assert " " not in sent_data, "Payload was not strictly minified"
        assert sent_data == '{"name":"test.com","spam_action":"disabled"}'


class TestAsyncClient:
    """Tests for AsyncClient."""

    def test_async_client_inherits_client(self) -> None:
        # Mocking AsyncClient init-related side effects
        with patch("httpx.AsyncClient"):
            client = AsyncClient(auth=("api", "key-123"))
            assert client.auth == ("api", "key-123")
            assert client.config.api_url == Config.DEFAULT_API_URL

    @patch("httpx.AsyncClient")
    def test_async_client_getattr_returns_async_endpoint_type(self, mock_httpx: MagicMock) -> None:
        client = AsyncClient(auth=("api", "key-123"))
        ep = client.domains
        assert isinstance(ep, AsyncEndpoint)
        assert ep._auth == ("api", "key-123")
        assert "domains" in str(ep._url["keys"]).lower()

    @pytest.mark.asyncio
    async def test_aclose_closes_httpx_client(self) -> None:
        # Mocking the client to avoid SSL context creation on Windows
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_instance = mock_client_class.return_value
            mock_instance.aclose = AsyncMock()

            client = AsyncClient()
            # Force initialization of the client property
            _ = client._client
            await client.aclose()
            mock_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_instance = mock_client_class.return_value
            mock_instance.aclose = AsyncMock()

            client = AsyncClient()
            async with client as c:
                assert c is client
                # Trigger internal client creation
                _ = client._client
            mock_instance.aclose.assert_called_once()

    @patch("mailgun.client.logger.error")
    @pytest.mark.asyncio
    async def test_api_call_truncates_long_error_response(
        self, mock_logger_error: MagicMock
    ) -> None:
        """Test async error responses longer than 500 characters are truncated."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text, spec=httpx.Response)
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_client.request = AsyncMock(return_value=mock_resp)

        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.get()

        mock_logger_error.assert_called_once()
        logged_text = mock_logger_error.call_args[0][4]
        assert len(logged_text) == 503
        assert logged_text.endswith("...")

    def test_async_validate_auth_sanitizes_input(self) -> None:
        """Test OWASP Header Injection prevention via SecurityGuard."""
        # Put the carriage return INSIDE the string so .strip() doesn't remove it
        with pytest.raises(ValueError, match="Header Injection risk"):
            SecurityGuard.validate_auth(("api", "key\rwithnewline"))

    def test_async_client_dir_includes_endpoints(self) -> None:
        """Test that IDE introspection via __dir__ exposes config endpoints."""
        with patch("httpx.AsyncClient"):
            client = AsyncClient()
            client_dir = dir(client)

            assert "messages" in client_dir
            assert "bounces" in client_dir
            assert "domains" in client_dir

    @patch("httpx.AsyncClient")
    def test_async_global_timeout_propagates_to_endpoint(self, mock_httpx: MagicMock) -> None:
        """Test, that timeout of AsyncClient used in AsyncEndpoints."""
        client = AsyncClient(auth=("api", "key"), timeout=25.0)
        ep = client.domains

        assert ep._timeout == 25.0

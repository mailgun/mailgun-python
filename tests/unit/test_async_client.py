"""Unit tests for mailgun.client (AsyncClient, AsyncEndpoint)."""

from unittest.mock import AsyncMock, patch
from unittest.mock import MagicMock

import httpx
import pytest

from mailgun.client import AsyncClient
from mailgun.client import AsyncEndpoint
from mailgun.client import Config
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
        await ep.create(data={"name": "test.com"})
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
        assert mock_client.request.call_args[1]["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_api_call_raises_timeout_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        with pytest.raises(TimeoutError):
            await ep.get()

    @pytest.mark.asyncio
    async def test_api_call_raises_api_error_on_request_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=httpx.RequestError("error"))
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
        # Для httpx перевіряємо аргумент "content", а не "data"
        assert mock_client.request.call_args[1]["content"] == '{"key": "value"}'


class TestAsyncClient:
    """Tests for AsyncClient."""

    def test_async_client_inherits_client(self) -> None:
        client = AsyncClient(auth=("api", "key"))
        assert isinstance(client, AsyncClient)
        assert client.auth == ("api", "key")
        assert client.config.api_url == Config.DEFAULT_API_URL

    def test_async_client_getattr_returns_async_endpoint_type(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
        client = AsyncClient(auth=("api", "key"))
        ep = client.domains

        assert ep is not None
        assert isinstance(ep, AsyncEndpoint)
        assert ep._auth == ("api", "key")
        assert "domains" in ep._url["keys"] or "domains" in str(ep._url).lower()

    @pytest.mark.asyncio
    async def test_aclose_closes_httpx_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
        client = AsyncClient(auth=("api", "key"))
        # Trigger _client creation
        _ = client.domains

        httpx_client_before = client._httpx_client
        assert httpx_client_before is None or not httpx_client_before.is_closed

        # Access property to create client
        _ = client._client
        await client.aclose()

        httpx_client_after = client._httpx_client
        assert httpx_client_after is not None
        assert httpx_client_after.is_closed

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        async with AsyncClient(auth=("api", "key")) as client:
            assert client is not None
            assert isinstance(client, AsyncClient)
        # After exit, client should be closed
        httpx_client = client._httpx_client
        assert httpx_client is None or httpx_client.is_closed

    @pytest.mark.asyncio
    @patch("mailgun.client.logger.error")
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

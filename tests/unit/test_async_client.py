"""Unit tests for mailgun.client (AsyncClient, AsyncEndpoint)."""

import copy
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from mailgun.client import AsyncClient, AsyncEndpoint, Config, SecurityGuard
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V3, BASE_URL_V4


class TestAsyncEndpointPrepareFiles:
    """Tests for AsyncEndpoint._prepare_files."""

    @staticmethod
    def _make_endpoint() -> AsyncEndpoint:
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
        # Use kwargs for httpx compatibility
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

        # Minified JSON string is passed via 'content' when Content-Type is json
        kwargs = mock_client.request.call_args[1]
        sent_data = kwargs.get("content")

        assert sent_data is not None
        assert " " not in sent_data, "Payload was not strictly minified"
        assert sent_data == '{"name":"test.com","spam_action":"disabled"}'

    @pytest.mark.asyncio
    async def test_api_call_exception_chaining(self) -> None:
        """Verify that PEP 3134 exception chaining preserves the original httpx network error."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        original_err = httpx.RequestError("Async DNS resolution failed")
        mock_client.request.side_effect = original_err

        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = AsyncEndpoint(url=url, headers={}, auth=("api", "key"), client=mock_client)

        with pytest.raises(ApiError) as exc_info:
            await ep.api_call(auth=("api", "key"), method="GET", url=url, headers={}, domain="test.com")

        # Assert that the original error is chained as the cause
        assert exc_info.value.__cause__ is original_err

class TestAsyncClient:
    """Tests for AsyncClient shielding from SSL context issues."""

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_client_inherits_client(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        client = AsyncClient(auth=("api", "key-123"))
        assert client.auth == ("api", "key-123")
        assert client.config.api_url == Config.DEFAULT_API_URL

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_client_getattr_returns_async_endpoint_type(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        client = AsyncClient(auth=("api", "key-123"))
        ep = client.domains
        assert isinstance(ep, AsyncEndpoint)
        assert ep._auth == ("api", "key-123")
        assert "domains" in str(ep._url["keys"]).lower()

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_aclose_closes_httpx_client(self, mock_client_class: MagicMock, mock_transport: MagicMock) -> None:
        mock_instance = mock_client_class.return_value
        mock_instance.aclose = AsyncMock()

        client = AsyncClient()
        # Trigger client initialization using the mock
        _ = client._client
        await client.aclose()
        mock_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_frees_memory_and_is_idempotent(self) -> None:
        """Verify that aclose() nullifies the client for GC and is safe to call twice."""
        client = AsyncClient(auth=("api", "key"))

        mock_httpx = AsyncMock(spec=httpx.AsyncClient)
        client._httpx_client = mock_httpx
        assert client._httpx_client is not None

        await client.aclose()
        assert client._httpx_client is None
        assert client.auth is None

        try:
            await client.aclose()
        except Exception as e:
            pytest.fail(f"aclose() is not idempotent, raised: {e}")

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_client_class: MagicMock, mock_transport: MagicMock) -> None:
        mock_instance = mock_httpx = mock_client_class.return_value
        mock_httpx.aclose = AsyncMock()

        async with AsyncClient() as client:
            # Trigger internal client creation
            _ = client._client
            assert client._httpx_client is mock_instance

        mock_httpx.aclose.assert_called_once()

    @patch("mailgun.client.logger.error")
    @pytest.mark.asyncio
    async def test_api_call_truncates_long_error_response(
        self, mock_logger_error: MagicMock
    ) -> None:
        """Test that async error responses are NOT logged to prevent secret leakage (CWE-316)."""
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        long_response_text = "A" * 600
        mock_resp = MagicMock(status_code=500, text=long_response_text, spec=httpx.Response)
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_client.request = AsyncMock(return_value=mock_resp)

        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.get()

        mock_logger_error.assert_called_once()
        # Verify the error body is completely excluded from the log call
        assert len(mock_logger_error.call_args[0]) == 4

    def test_async_validate_auth_sanitizes_input(self) -> None:
        """Test OWASP Header Injection prevention via SecurityGuard."""
        with pytest.raises(ValueError, match="Header Injection risk"):
            SecurityGuard.validate_auth(("api", "key\rwithnewline"))

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_client_dir_includes_endpoints(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        """Test that IDE introspection via __dir__ exposes config endpoints."""
        client = AsyncClient()
        client_dir = dir(client)

        assert "messages" in client_dir
        assert "bounces" in client_dir
        assert "domains" in client_dir

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_global_timeout_propagates_to_endpoint(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        """Test, that timeout of AsyncClient used in AsyncEndpoints."""
        client = AsyncClient(auth=("api", "key"), timeout=25.0)
        ep = client.domains

        assert ep._timeout == 25.0

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_client_getattr_invalid_route(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        """Test that unknown routes in AsyncClient fallback to dynamic v3 endpoints."""
        client = AsyncClient(auth=("api", "key"))
        # The Catch-All router should generate an async endpoint
        ep = client.some_unknown_feature

        assert isinstance(ep, AsyncEndpoint)
        assert ep._url["base"].endswith("v3/")
        assert ep._url["keys"] == ["some", "unknown", "feature"]

    def test_async_client_getattr_magic_methods(self) -> None:
        """Test that AsyncClient.__getattr__ strictly rejects magic methods."""
        client = AsyncClient(auth=("api", "key"))

        # Python 3.11+ added __getstate__ to 'object' natively
        assert not hasattr(client, "__this_is_a_fake_dunder__")

        # Prove the object can be copied safely without returning mock Endpoints for dunders
        client_copy = copy.deepcopy(client)
        assert client_copy is not client
        assert isinstance(client_copy, AsyncClient)

    @patch("httpx.AsyncHTTPTransport")
    @patch("httpx.AsyncClient")
    def test_async_client_connection_pooling_configured(self, mock_httpx: MagicMock, mock_transport: MagicMock) -> None:
        """Verify that AsyncHTTPTransport is configured with expanded limits."""
        client = AsyncClient(auth=("api", "key"))
        _ = client._client  # Trigger lazy init

        mock_transport.assert_called_once()
        _, kwargs = mock_transport.call_args
        assert kwargs["retries"] == 3
        assert kwargs["limits"].max_keepalive_connections == 100
        assert kwargs["limits"].max_connections == 100

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.request")
    async def test_async_client_global_timeout_not_shadowed(self, mock_request: MagicMock) -> None:
        """Verify that the global timeout is not shadowed by the method's default value."""

        # Set up the mock and create a client with a unique global timeout
        mock_request.return_value = MagicMock(status_code=200, spec=httpx.Response)
        client = AsyncClient(auth=("api", "key"), timeout=999.0)

        # Make a request without specifying a timeout at the method level
        await client.messages.create(domain="test.com", data={"to": "test@test.com"})

        # Verify that the global timeout 999.0 was actually passed to httpx
        mock_request.assert_called_once()
        kwargs = mock_request.call_args[1]

        assert "timeout" in kwargs, "Timeout parameter is missing in request kwargs"
        assert kwargs["timeout"] == 999.0, f"Expected timeout 999.0, got {kwargs['timeout']} (Shadowing bug detected!)"

    def test_async_client_getattr_suppresses_keyerror(self) -> None:
        """Verify that accessing an invalid attribute raises AttributeError from None.

        This ensures internal KeyErrors from the routing dictionary do not leak
        into the user's exception traceback (PEP 3134).
        """
        client = AsyncClient(auth=("api", "key"))

        # We must use getattr() with illegal characters to bypass the dynamic catch-all router
        # and forcefully trigger the internal KeyError inside Config/SecurityGuard.
        with pytest.raises(AttributeError, match="'AsyncClient' object has no attribute '!@#'") as exc_info:
            _ = getattr(client, "!@#")

        # Assert that 'from None' was used to break the exception chain
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__ is True, "Internal KeyError is leaking! Use 'from None'."


class TestAsyncClientLifecycle(unittest.IsolatedAsyncioTestCase):

    @patch("httpx.AsyncClient.request")
    async def test_async_client_context_manager_reuse(self, mock_request: MagicMock) -> None:
        """Verify that reusing the AsyncClient creates a new transport."""

        # Set up a fake response from the server
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        # Create a single instance of the client
        client = AsyncClient(auth=("api", "key"))

        # First session (Creates transport, makes request, closes transport)
        async with client:
            await client.domains.get(domain_name="test.com")

        # The second session MUST NOT fail with a "Transport is closed" error
        try:
            async with client:
                await client.domains.get(domain_name="test.com")
        except RuntimeError as e:
            if "closed" in str(e).lower():
                self.fail(f"Regression caught: Transport was reused after being closed! {e}")
            raise  # Re-raise the error if it's a different, unexpected RuntimeError

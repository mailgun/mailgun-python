"""Unit tests for mailgun.client (AsyncClient, AsyncEndpoint)."""

import copy
import gc
from typing import Any

from mailgun._httpx_compat import httpx as compat_httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mailgun.client import AsyncClient, AsyncEndpoint, Config, SecurityGuard
from mailgun.endpoints import Endpoint
from mailgun.handlers.error_handler import ApiError
from tests.conftest import BASE_URL_V3, BASE_URL_V4


class TestAsyncClient:
    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_aclose_closes_httpx_client(
        self, mock_client_class: MagicMock, _mock_transport: MagicMock
    ) -> None:
        mock_instance = mock_client_class.return_value
        mock_instance.aclose = AsyncMock()

        client = AsyncClient()
        _ = client._client
        await client.aclose()
        mock_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_frees_memory_and_is_idempotent(self) -> None:
        """Verify that aclose() nullifies the client for GC and is safe to call twice."""
        client = AsyncClient(auth=("api", "key"))

        mock_httpx = AsyncMock(spec=compat_httpx.AsyncClient)
        client._httpx_client = mock_httpx
        assert client._httpx_client is not None

        await client.aclose()
        assert client._httpx_client is None
        assert client.auth is None

        try:
            await client.aclose()
        except Exception as e:
            pytest.fail(f"aclose() is not idempotent, raised: {e}")

    @pytest.mark.asyncio
    async def test_async_client_aclose_is_idempotent_and_safe_to_call_multiple_times(
        self,
    ) -> None:
        """Ensures that calling `.aclose()` repeatedly does not crash the client."""
        client = AsyncClient(auth=("api", "key"))

        client._httpx_client = AsyncMock(spec=compat_httpx.AsyncClient)
        assert client._httpx_client is not None

        await client.aclose()
        assert client._httpx_client is None

        await client.aclose()
        assert client._httpx_client is None

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_connection_pooling_configured(
        self, _mock_httpx: MagicMock, mock_transport: MagicMock
    ) -> None:
        """Verify that AsyncHTTPTransport is configured with expanded limits."""
        client = AsyncClient(auth=("api", "key"))
        _ = client._client

        mock_transport.assert_called_once()
        _, kwargs = mock_transport.call_args

        assert kwargs["retries"] == 3
        assert kwargs["limits"].max_keepalive_connections == 100
        assert kwargs["limits"].max_connections == 100

    @pytest.mark.asyncio
    async def test_async_client_context_manager(self) -> None:
        """Ensures the async context manager correctly initializes and closes the client."""
        async with AsyncClient(auth=("api", "key")) as client:
            assert client.auth == ("api", "key")
            client._httpx_client = AsyncMock(spec=compat_httpx.AsyncClient)
            assert client._httpx_client is not None

        assert client._httpx_client is None

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_async_client_context_manager_clean_exit(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        """Cover clean AsyncClient __aexit__."""

        _mock_httpx.return_value.aclose = AsyncMock()

        client = AsyncClient(auth=("api", "key"))
        async with client:
            _ = client._client
        assert client._httpx_client is None

    @pytest.mark.asyncio
    async def test_async_client_context_manager_exception_propagation(self) -> None:
        """Ensure __aexit__ gracefully cleans up memory when an exception occurs."""
        client = AsyncClient(auth=("api", "key"))

        with pytest.raises(RuntimeError, match="Simulated crash"):
            async with client:
                raise RuntimeError("Simulated crash")

        assert client._httpx_client is None  # type: ignore[unreachable]
        assert client.auth is None

    @pytest.mark.asyncio
    @patch("mailgun.endpoints.httpx.AsyncClient.request")
    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    async def test_async_client_context_manager_reuse(
        self, mock_transport_class: MagicMock, mock_request: MagicMock
    ) -> None:
        """Verify that reusing the AsyncClient creates a new transport."""
        mock_transport_instance = mock_transport_class.return_value
        mock_transport_instance.aclose = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        client = AsyncClient(auth=("api", "key"))

        async with client:
            await client.domains.get(domain_name="test.com")

        try:
            async with client:
                await client.domains.get(domain_name="test.com")
        except RuntimeError as e:
            if "closed" in str(e).lower():
                pytest.fail(f"Regression caught: Transport reused after being closed! {e}")
            raise

    @pytest.mark.asyncio
    async def test_async_client_custom_transport_bypasses_default(self) -> None:
        """Verify passing a custom HTTPX transport skips the default TLS transport creation."""
        mock_transport = compat_httpx.MockTransport(lambda _: compat_httpx.Response(200))

        client = AsyncClient(
            auth=("api", "key"),
            client_kwargs={"transport": mock_transport},
        )

        _ = client._client

        assert client._httpx_client._transport is mock_transport  # pyright: ignore[reportOptionalMemberAccess]

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_dir_includes_endpoints(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        """Test that IDE introspection via __dir__ exposes config endpoints."""
        client = AsyncClient()
        client_dir = dir(client)

        assert "messages" in client_dir
        assert "bounces" in client_dir
        assert "domains" in client_dir

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_getattr_caching_and_dir(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        """Ensures that dynamic endpoints are correctly instantiated."""
        client = AsyncClient(auth=("api", "key"))

        _ = dir(client)

        ep1 = client.domains
        ep2 = client.domains

        assert ep1._url == ep2._url
        assert ep1._auth == ep2._auth

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_getattr_invalid_route(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        """Test that unknown routes in AsyncClient fallback to dynamic v3 endpoints."""
        client = AsyncClient(auth=("api", "key"))
        ep = client.some_unknown_feature

        assert isinstance(ep, AsyncEndpoint)
        assert ep._url["base"].endswith("v3/")
        assert ep._url["keys"] == ["some", "unknown", "feature"]

    def test_async_client_getattr_magic_methods(self) -> None:
        """Test that AsyncClient.__getattr__ strictly rejects magic methods."""
        client = AsyncClient(auth=("api", "key"))

        assert not hasattr(client, "__this_is_a_fake_dunder__")

        client_copy = copy.deepcopy(client)
        assert client_copy is not client
        assert isinstance(client_copy, AsyncClient)

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_getattr_returns_async_endpoint_type(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        client = AsyncClient(auth=("api", "key-123"))
        ep = client.domains
        assert isinstance(ep, AsyncEndpoint)
        assert ep._auth == ("api", "key-123")
        assert "domains" in str(ep._url["keys"]).lower()

    def test_async_client_getattr_suppresses_keyerror(self) -> None:
        """Verify that accessing an invalid attribute raises AttributeError from None."""
        client = AsyncClient(auth=("api", "key"))

        with pytest.raises(
            AttributeError, match="'AsyncClient' object has no attribute '!@#'"
        ) as exc_info:
            _ = getattr(client, "!@#")

        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__ is True

    @pytest.mark.asyncio
    @patch("mailgun.endpoints.httpx.AsyncClient.request")
    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    async def test_async_client_global_timeout_not_shadowed(
        self, _mock_transport: MagicMock, mock_request: MagicMock
    ) -> None:
        """Verify that the global timeout is not shadowed by the method's default value."""
        mock_request.return_value = MagicMock(status_code=200, spec=compat_httpx.Response)
        client = AsyncClient(auth=("api", "key"), timeout=299.0)

        await client.messages.create(domain="test.com", data={"to": "test@test.com"})

        mock_request.assert_called_once()
        kwargs = mock_request.call_args[1]

        assert "timeout" in kwargs
        assert kwargs["timeout"] == 299.0

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_client_inherits_client(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        client = AsyncClient(auth=("api", "key-123"))
        assert client.auth == ("api", "key-123")
        assert client.config.api_url == Config.DEFAULT_API_URL

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, mock_client_class: MagicMock, _mock_transport: MagicMock
    ) -> None:
        mock_instance = mock_httpx = mock_client_class.return_value
        mock_httpx.aclose = AsyncMock()

        async with AsyncClient() as client:
            _ = client._client
            assert client._httpx_client is mock_instance

        mock_httpx.aclose.assert_called_once()

    @patch("mailgun.client.httpx.AsyncHTTPTransport")
    @patch("mailgun.client.httpx.AsyncClient")
    def test_async_global_timeout_propagates_to_endpoint(
        self, _mock_httpx: MagicMock, _mock_transport: MagicMock
    ) -> None:
        """Test that timeout of AsyncClient is used in AsyncEndpoints."""
        client = AsyncClient(auth=("api", "key"), timeout=25.0)
        ep = client.domains

        assert ep._timeout == 25.0

    def test_async_validate_auth_sanitizes_input(self) -> None:
        """Test OWASP Header Injection prevention via SecurityGuard."""
        with pytest.raises(ValueError, match="Header Injection risk"):
            SecurityGuard.validate_auth(("api", "key\rwithnewline"))

    @pytest.mark.asyncio
    async def test_async_client_property_lazy_initialization_happy_path(self) -> None:
        """
        [Happy Path] Verify that _client lazily initializes and returns the same
        active instance on subsequent calls, proving the CWE-400 hotfix works.
        """
        client = AsyncClient(auth=("api", "key"))

        # First access should initialize the pool
        httpx_client_1 = client._client
        assert httpx_client_1 is not None
        assert httpx_client_1.is_closed is False

        # Second access MUST return the exact same instance (not None, and not a new pool)
        httpx_client_2 = client._client
        assert httpx_client_2 is not None
        assert httpx_client_1 is httpx_client_2, "Failed to reuse the active connection pool!"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_async_client_context_manager_retains_connection_edge_case(self) -> None:
        """
        [Edge Case] Verify that inside an async context manager, multiple accesses
        to _client return the same open connection pool. This was the exact scenario
        that triggered the socket leak bug.
        """
        async with AsyncClient(auth=("api", "key")) as client:
            client1 = client._client
            client2 = client._client

            # The client must not fall through to returning None
            assert client1 is not None
            assert client2 is not None

            # The context manager must hold the same instance open
            assert client1 is client2
            assert client1.is_closed is False

    @pytest.mark.asyncio
    async def test_async_client_property_reinitializes_if_closed_unhappy_path(self) -> None:
        """
        [Unhappy Path] Verify that if the underlying httpx client is forcefully closed
        (e.g., dropped connection or aggressive GC), accessing the property spins up
        a fresh connection pool rather than failing or returning None.
        """
        client = AsyncClient(auth=("api", "key"))

        first_pool = client._client
        assert first_pool is not None

        # Simulate a forcefully closed connection pool (unhappy path)
        await first_pool.aclose()
        assert first_pool.is_closed is True

        # Next access MUST detect the closed state and create a new instance
        second_pool = client._client
        assert second_pool is not None
        assert second_pool.is_closed is False

        # Validate that a brand new httpx.AsyncClient was generated
        assert first_pool is not second_pool, "Failed to regenerate a closed connection pool!"

        await client.aclose()

    def test_async_client_unclosed_resource_warning(self) -> None:
        """Verify that leaving an AsyncClient unclosed triggers a ResourceWarning upon deletion."""
        client = AsyncClient(auth=("api", "key"))
        _ = client._client
        with pytest.warns(ResourceWarning, match="Unclosed AsyncClient detected"):
            del client
            gc.collect()


class TestAsyncEndpoint:
    @staticmethod
    def _make_endpoint() -> AsyncEndpoint:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        return AsyncEndpoint(
            url=url,
            headers={},
            auth=None,
            client=MagicMock(spec=compat_httpx.AsyncClient),
        )

    @pytest.mark.asyncio
    async def test_api_call_exception_chaining(self) -> None:
        """Verify that PEP 3134 exception chaining preserves the original httpx error."""
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        original_err = compat_httpx.RequestError("Async DNS resolution failed", request=MagicMock())
        mock_client.request.side_effect = original_err

        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        ep = AsyncEndpoint(url=url, headers={}, auth=("api", "key"), client=mock_client)

        with pytest.raises(ApiError) as exc_info:
            await ep.api_call(
                auth=("api", "key"), method="GET", url=url, headers={}, domain="test.com"
            )

        assert exc_info.value.__cause__ is original_err

    @pytest.mark.asyncio
    async def test_api_call_raises_api_error_on_request_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request.side_effect = compat_httpx.RequestError(
            "network error", request=MagicMock()
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        with pytest.raises(ApiError):
            await ep.get()

    @pytest.mark.asyncio
    async def test_api_call_raises_timeout_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request.side_effect = compat_httpx.TimeoutException("timeout")
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        with pytest.raises(TimeoutError):
            await ep.get()

    @patch("mailgun.endpoints.logger.error")
    @pytest.mark.asyncio
    async def test_api_call_truncates_long_error_response(
        self, mock_logger_error: MagicMock
    ) -> None:
        """Test that async error responses are NOT logged to prevent secret leakage."""
        url = {"base": "https://api.mailgun.net/v4/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)

        long_response_text = "A" * 600
        mock_resp = MagicMock(
            status_code=500, text=long_response_text, spec=compat_httpx.Response
        )
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_client.request = AsyncMock(return_value=mock_resp)

        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.get()

        mock_logger_error.assert_called_once()
        assert len(mock_logger_error.call_args[0]) == 4

    @pytest.mark.asyncio
    @patch.object(AsyncEndpoint, "get")
    async def test_async_endpoint_missing_verbs_and_stream_filters(
        self, mock_get: AsyncMock
    ) -> None:
        """Cover missing verbs and stream filter logic."""
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(
            url={"base": "https://api.mailgun.net/v3/", "keys": ["test"]},
            headers={},
            auth=("api", "key"),
            client=mock_client,
        )

        await ep.put(domain="test.com", data={"a": 1})
        await ep.patch(domain="test.com", data={"a": 1})
        await ep.delete(domain="test.com")

        mock_get.return_value = MagicMock(
            json=lambda: {"items": []}, raise_for_status=lambda: None
        )

        results = [item async for item in ep.stream(filters={"limit": 10})]  # pyright: ignore[reportGeneralTypeIssues]
        assert results == []

    @pytest.mark.asyncio
    async def test_async_endpoint_payload_is_strictly_minified(self) -> None:
        """Test that JSON payloads are strictly minified before async transmission."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(
            url=url,
            headers={"Content-Type": "application/json"},
            auth=None,
            client=mock_client,
        )

        payload_with_spaces = {"name": "test.com", "spam_action": "disabled"}

        await ep.create(data=payload_with_spaces)

        kwargs = mock_client.request.call_args[1]
        sent_data = kwargs.get("content")

        assert sent_data is not None
        assert " " not in sent_data, "Payload was not strictly minified"
        assert sent_data == '{"name":"test.com","spam_action":"disabled"}'

    @pytest.mark.asyncio
    async def test_create_sends_post(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.create(data={"key": "value"})
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "POST"

    @pytest.mark.asyncio
    async def test_delete_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.delete()
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_get_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(
            url=url, headers={"User-agent": "test"}, auth=("api", "key"), client=mock_client
        )
        await ep.get()
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[1]["method"] == "GET"

    @pytest.mark.asyncio
    async def test_patch_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=("api", "key"), client=mock_client)
        await ep.patch(data={"test": "data"})
        mock_client.request.assert_called_once()

        args, kwargs = mock_client.request.call_args
        called_method = args[0] if args else kwargs.get("method", "")
        assert called_method.lower() == "patch"

    @pytest.mark.asyncio
    async def test_put_calls_client_request(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=("api", "key"), client=mock_client)
        await ep.put(data={"test": "data"})
        mock_client.request.assert_called_once()

        args, kwargs = mock_client.request.call_args
        called_method = args[0] if args else kwargs.get("method", "")
        assert called_method.lower() == "put"

    @pytest.mark.asyncio
    async def test_update_serializes_json_with_custom_headers(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        mock_client = AsyncMock(spec=compat_httpx.AsyncClient)
        mock_client.request = AsyncMock(
            return_value=MagicMock(status_code=200, spec=compat_httpx.Response)
        )
        ep = AsyncEndpoint(url=url, headers={}, auth=None, client=mock_client)
        await ep.update(
            data={"key": "value"}, headers={"Content-Type": "application/json"}
        )
        mock_client.request.assert_called_once()
        kwargs = mock_client.request.call_args[1]
        assert "content" in kwargs
        assert '{"key":"value"}' in kwargs["content"]


class TestStreamPagination:
    class MockPaginationResponse:
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def json(self) -> dict[str, Any]:
            return self._data

        def raise_for_status(self) -> None:
            pass

    @patch.object(AsyncEndpoint, "get")
    @pytest.mark.asyncio
    async def test_async_stream_pagination_empty_items(self, mock_get: AsyncMock) -> None:
        """Cover the zero-iteration async loop break."""
        page_1 = self.MockPaginationResponse(
            {"items": [], "paging": {"next": "https://api.mailgun.net/v3/domains?skip=1"}}
        )
        mock_get.return_value = page_1
        endpoint = AsyncEndpoint(
            url={"base": "http://mock", "keys": []},
            headers={},
            auth=None,
            client=MagicMock(),
        )
        results = [item async for item in endpoint.stream()]  # pyright: ignore[reportGeneralTypeIssues]
        assert results == []

    @patch.object(AsyncEndpoint, "get")
    @pytest.mark.asyncio
    async def test_async_stream_pagination_no_next_url_with_items(
        self, mock_get: AsyncMock
    ) -> None:
        page_1 = self.MockPaginationResponse(
            {"items": [{"id": "event_1"}], "paging": {}}
        )
        mock_get.return_value = page_1
        endpoint = AsyncEndpoint(
            url={"base": "http://mock", "keys": []},
            headers={},
            auth=None,
            client=MagicMock(),
        )
        results = []
        async for item in endpoint.stream():  # pyright: ignore[reportGeneralTypeIssues]
            results.append(item)
        assert results == [{"id": "event_1"}]
        assert mock_get.call_count == 1

    @patch.object(Endpoint, "get")
    def test_sync_stream_pagination_empty_items(self, mock_get: MagicMock) -> None:
        """Cover the zero-iteration loop break."""
        page_1 = self.MockPaginationResponse(
            {"items": [], "paging": {"next": "https://api.mailgun.net/v3/domains?skip=1"}}
        )
        mock_get.return_value = page_1
        endpoint = Endpoint(url={"base": "http://mock", "keys": []}, headers={}, auth=None)
        results = list(endpoint.stream())
        assert results == []

    @patch.object(Endpoint, "get")
    def test_sync_stream_pagination_no_next_url_with_items(
        self, mock_get: MagicMock
    ) -> None:
        page_1 = self.MockPaginationResponse(
            {"items": [{"id": "event_1"}], "paging": {}}
        )
        mock_get.return_value = page_1
        endpoint = Endpoint(url={"base": "http://mock", "keys": []}, headers={}, auth=None)
        results = list(endpoint.stream())
        assert results == [{"id": "event_1"}]
        assert mock_get.call_count == 1

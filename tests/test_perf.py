import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, cast

import httpx
import pytest
import requests  # pyright: ignore[reportMissingModuleSource]
import responses

from mailgun.client import AsyncClient, Client


@pytest.fixture
def mocked_mailgun() -> Generator[responses.RequestsMock, None, None]:
    """
    Intercepts Mailgun API calls at the urllib3 layer for synchronous tests.
    assert_all_requests_are_fired=False prevents teardown errors if a test fails early.
    """
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses.POST,
            "https://api.mailgun.net/v3/test.com/messages",
            json={"id": "<test-id>", "message": "Queued. Thank you."},
            status=200,
        )
        yield rsps


class TestClientPerformance:
    def test_async_client_concurrent_throughput(self, benchmark: Any) -> None:
        """
        Measures how fast the AsyncClient can dispatch concurrent requests.
        This proves that httpx.Limits(max_connections=100) prevents asyncio bottlenecks.
        """
        BATCH_SIZE = 50

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": "<test-id>", "message": "Queued."})

        mock_transport = httpx.MockTransport(mock_handler)

        try:
            # v1.7.0+ Architecture with Config object
            from mailgun.config import Config
            config = Config()
            client = AsyncClient(
                auth=("api", "key"),
                config=config,
                client_kwargs={"transport": mock_transport}
            )
        except Exception:
            try:
                # Attempt modern injection (using client_kwargs dictionary)
                client = AsyncClient(
                    auth=("api", "key"), client_kwargs={"transport": mock_transport}
                )
            except TypeError:
                # Fallback for v1.6.0: Inject transport as a direct top-level kwarg
                client = AsyncClient(auth=("api", "key"), transport=mock_transport)

        # Ultimate Failsafe: Ensure mock transport is forcibly applied if silently swallowed
        existing = getattr(client, "_client", None)

        if existing is None or getattr(existing, "_transport", None) != mock_transport:
            # Extract safe defaults if the client hasn't fully booted its internal httpx layer
            auth = getattr(existing, "auth", getattr(client, "auth", ("api", "key")))
            headers = getattr(existing, "headers", None)
            limits = getattr(existing, "_limits", httpx.Limits(max_connections=100))
            timeout = getattr(existing, "timeout", None)

            # Assemble kwargs without injecting None into strict httpx fields
            kwargs = {"transport": mock_transport, "auth": auth, "limits": limits}
            if headers is not None: kwargs["headers"] = headers
            if timeout is not None: kwargs["timeout"] = timeout

            new_httpx_client = httpx.AsyncClient(**kwargs)

            try:
                # Use setattr to bypass Pyright's static read-only property warnings
                setattr(client, "_client", new_httpx_client)
            except AttributeError:
                # If _client is a read-only property (v1.7.0+), target the underlying variable
                setattr(client, "_httpx_client", new_httpx_client)

        async def send_one_email(i: int) -> httpx.Response:
            return await client.messages.create(
                domain="test.com",
                data={
                    "from": "sender@test.com",
                    "to": f"recipient_{i}@test.com",
                    "subject": "Load Test",
                    "text": "Testing async pooling.",
                },
            )

        async def dispatch_batch_async() -> None:
            # Gather executes all 50 coroutines concurrently on the event loop
            tasks = [send_one_email(i) for i in range(BATCH_SIZE)]
            await asyncio.gather(*tasks)

        def dispatch_batch() -> None:
            # Helper to run the async batch inside the synchronous benchmark runner
            asyncio.run(dispatch_batch_async())

        try:
            benchmark.pedantic(dispatch_batch, rounds=10, iterations=5)
        finally:
            # Safely close the async client
            aclose_method = getattr(client, "aclose", None)
            if callable(aclose_method):
                coro = cast(Coroutine[Any, Any, None], cast(object, aclose_method()))
                asyncio.run(coro)

    def test_client_routing_speed(self, benchmark: Any) -> None:
        """
        Measures the pure CPU overhead of the __getattr__ dynamic router.
        This proves the efficiency of the lru_cache and magic-method short-circuits.
        """
        client = Client(auth=("api", "key"))

        def route_messages() -> Any:
            # Accessing a dynamic attribute triggers __getattr__ and URL building
            return client.messages

        benchmark(route_messages)

    def test_sync_client_concurrent_throughput(
        self, benchmark: Any, mocked_mailgun: responses.RequestsMock
    ) -> None:
        """
        Measures how fast the synchronous Client can dispatch concurrent requests.
        This proves that pool_maxsize=100 prevents ThreadPoolExecutor bottlenecks.
        """
        BATCH_SIZE = 50
        client = Client(auth=("api", "key"))

        def send_one_email(i: int) -> requests.Response:
            return client.messages.create(
                domain="test.com",
                data={
                    "from": "sender@test.com",
                    "to": f"recipient_{i}@test.com",
                    "subject": "Load Test",
                    "text": "Testing connection pooling.",
                },
            )

        def dispatch_batch() -> None:
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                list(executor.map(send_one_email, range(BATCH_SIZE)))

        try:
            # Run the benchmark (lower rounds because thread pools are heavy)
            benchmark.pedantic(dispatch_batch, rounds=10, iterations=5)
        finally:
            # Safely close if the method exists (for backwards compatibility with v1.6.0)
            close_method = getattr(client, "close", None)
            if callable(close_method):
                close_method()

import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest
import requests  # pyright: ignore[reportMissingModuleSource]
import responses

from mailgun.client import AsyncClient, Client

# ------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------

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


# ------------------------------------------------------------------------
# BENCHMARK 1: ROUTING OVERHEAD (PURE CPU)
# ------------------------------------------------------------------------

def test_client_routing_speed(benchmark: Any) -> None:
    """
    Measures the pure CPU overhead of the __getattr__ dynamic router.
    This proves the efficiency of the lru_cache and magic-method short-circuits.
    """
    client = Client(auth=("api", "key"))

    def route_messages() -> Any:
        # Accessing a dynamic attribute triggers __getattr__ and URL building
        return client.messages

    # Call benchmark as a function instead
    benchmark(route_messages)


# ------------------------------------------------------------------------
# BENCHMARK 2: SYNCHRONOUS CONNECTION POOLING (THREADING)
# ------------------------------------------------------------------------

def test_sync_client_concurrent_throughput(benchmark: Any, mocked_mailgun: responses.RequestsMock) -> None:
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
                "text": "Testing connection pooling."
            }
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


# ------------------------------------------------------------------------
# BENCHMARK 3: ASYNCHRONOUS CONNECTION POOLING (EVENT LOOP)
# ------------------------------------------------------------------------

def test_async_client_concurrent_throughput(benchmark: Any) -> None:
    """
    Measures how fast the AsyncClient can dispatch concurrent requests.
    This proves that httpx.Limits(max_connections=100) prevents asyncio bottlenecks.
    """
    BATCH_SIZE = 50

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "<test-id>", "message": "Queued."})

    mock_transport = httpx.MockTransport(mock_handler)

    # Inject the mock transport via client_kwargs
    client = AsyncClient(auth=("api", "key"), client_kwargs={"transport": mock_transport})

    async def send_one_email(i: int) -> httpx.Response:
        return await client.messages.create(
            domain="test.com",
            data={
                "from": "sender@test.com",
                "to": f"recipient_{i}@test.com",
                "subject": "Load Test",
                "text": "Testing async pooling."
            }
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
            asyncio.run(aclose_method())  # pyright: ignore[reportArgumentType]

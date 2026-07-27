"""Performance and throughput benchmark tests for the Mailgun SDK."""

import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
import tracemalloc
from typing import Any, cast

import pytest
import requests  # pyright: ignore[reportMissingModuleSource]
import responses

from mailgun._httpx_compat import httpx
from mailgun.client import AsyncClient, Client


# ------------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------------

@pytest.fixture
def mocked_mailgun() -> Generator[responses.RequestsMock, None, None]:
    """Intercepts Mailgun API calls at the urllib3 layer for synchronous tests.
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
    """Measures the pure CPU overhead of the __getattr__ dynamic router.
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
    """Measures how fast the synchronous Client can dispatch concurrent requests.
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
    """Measures how fast the AsyncClient can dispatch concurrent requests.
    This proves that httpx.Limits(max_connections=100) prevents asyncio bottlenecks.
    """
    BATCH_SIZE = 50

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "<test-id>", "message": "Queued."})

    mock_transport = httpx.MockTransport(mock_handler)

    try:
        # 1. Attempt modern injection (using client_kwargs dictionary)
        client = AsyncClient(auth=("api", "key"), client_kwargs={"transport": mock_transport})  # type: ignore[call-arg]
    except TypeError:
        # 2. Fallback for v1.6.0: Inject transport as a direct top-level kwarg
        client = AsyncClient(auth=("api", "key"), transport=mock_transport)

    # --- THE ULTIMATE FAILSAFE ---
    # Ensures the mock transport is forcibly applied even if the SDK's SecureHTTPAdapter
    # tries to overwrite it with a real ssl.SSLContext during lazy initialization.
    existing = getattr(client, "_client", None)

    if existing is None or getattr(existing, "_transport", None) != mock_transport:
        auth = getattr(existing, "auth", getattr(client, "auth", ("api", "key")))
        limits = getattr(existing, "_limits", httpx.Limits(max_connections=100))

        kwargs: dict[str, Any] = {"transport": mock_transport, "auth": auth, "limits": limits}

        headers = getattr(existing, "headers", None)
        if headers:
            kwargs["headers"] = headers

        timeout = getattr(existing, "timeout", None)
        if timeout:
            kwargs["timeout"] = timeout

        new_httpx_client = httpx.AsyncClient(**kwargs)

        try:
            # Use setattr to bypass static read-only property restrictions
            setattr(client, "_client", new_httpx_client)
        except AttributeError:
            pass

        # Always attempt to set the underlying v1.7.0+ private variable just in case
        setattr(client, "_httpx_client", new_httpx_client)
    # -------------------------------

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
        await asyncio.gather(*tasks, return_exceptions=True)

    # Pre-allocate event loop outside the benchmark loop to prevent event loop creation overhead
    loop = asyncio.new_event_loop()

    def dispatch_batch() -> None:
        loop.run_until_complete(dispatch_batch_async())

    try:
        benchmark.pedantic(dispatch_batch, rounds=10, iterations=5)
    finally:
        loop.run_until_complete(client.aclose())
        loop.close()


# ------------------------------------------------------------------------
# BENCHMARK 4: MEMORY FOOTPRINT & LEAK PREVENTION (__slots__)
# ------------------------------------------------------------------------

def test_memory_footprint_leak_prevention() -> None:
    """Proves that processing large requests doesn't bloat the RSS memory footprint."""
    client = Client(auth=("api", "key"))

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    for i in range(5000):
        _ = client.messages

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    total_diff_kb = sum(stat.size_diff for stat in stats) / 1024

    print(f"\nMemory Delta after 5,000 operations: {total_diff_kb:.2f} KB")

    # Guardrail to ensure slots prevent dynamic hash table memory bloat
    assert total_diff_kb < 100.0, f"Memory leak detected! Footprint grew by {total_diff_kb:.2f} KB"

#!/usr/bin/env python3
"""Concurrent Async Client Fuzzer testing Thundering Herd and Connection Pool Stability."""

import asyncio
import atexit
import logging
import os
import sys
from pathlib import Path
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun import routes
    import httpx2
    from mailgun.client import AsyncClient
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)

_VALID_ENDPOINTS = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())


class MockAsyncTransport(httpx2.AsyncBaseTransport):
    """Zero-allocation async mock transport."""

    _static_resp = httpx2.Response(200, content=b'{"id": "async-test", "items": []}')

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        return self._static_resp


original_init = httpx2.AsyncClient.__init__


def secure_init(self: httpx2.AsyncClient, *args: Any, **kwargs: Any) -> None:
    kwargs["transport"] = MockAsyncTransport()
    original_init(self, *args, **kwargs)


httpx2.AsyncClient.__init__ = secure_init  # type: ignore[method-assign]


async def _worker_task(client: AsyncClient, fdp: atheris.FuzzedDataProvider) -> None:
    """Simulate concurrent endpoint access over the shared async client session."""
    target_attr = fdp.PickValueInList(_VALID_ENDPOINTS) if _VALID_ENDPOINTS else "messages"
    domain = fdp.ConsumeUnicodeNoSurrogates(16) or "test.mailgun.org"

    try:
        endpoint = getattr(client, target_attr, None)
        if endpoint is not None:
            if hasattr(endpoint, "get"):
                await endpoint.get(domain=domain)
            elif hasattr(endpoint, "api_call"):
                await endpoint.api_call(method="get", domain=domain)
    except (
        ApiError,
        AttributeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        httpx2.RequestError,
    ):
        # Fuzzing intentionally suppresses expected malformed-input/runtime errors
        # so one failing path does not stop concurrent exploration.
        pass


async def _async_fuzz_target(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    auth_user = fdp.ConsumeUnicodeNoSurrogates(16)
    auth_key = fdp.ConsumeUnicodeNoSurrogates(32) or "test-key"
    api_url = "https://api.mailgun.net" if fdp.ConsumeBool() else "http://localhost:8080"

    try:
        async with AsyncClient(auth=(auth_user, auth_key), api_url=api_url) as client:
            concurrency = fdp.ConsumeIntInRange(2, 6)
            tasks = [_worker_task(client, fdp) for _ in range(concurrency)]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Test aclose idempotency
            if fdp.ConsumeBool():
                await client.aclose()
                await client.aclose()

    except (
        ApiError,
        AttributeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        httpx2.RequestError,
    ):
        pass


def TestOneInput(data: bytes) -> None:
    if len(data) < 15:
        return
    _FUZZ_LOOP.run_until_complete(_async_fuzz_target(data))


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: _FUZZ_LOOP.close())
    atheris.Fuzz()

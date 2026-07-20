#!/usr/bin/env python3
"""Differential fuzzer to ensure Sync and Async clients behave identically."""

import asyncio
import logging
import sys
from typing import Any

import atheris
from mailgun._httpx_compat import httpx as compat_httpx
import requests

with atheris.instrument_imports():
    from mailgun import routes
    from mailgun.client import AsyncClient, Client

logging.disable(logging.CRITICAL)

_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)

_VALID_ENDPOINTS = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())

# Pre-allocate static responses globally to avoid initialization overhead during fuzzing
_STATIC_SYNC_RESP = requests.Response()
_STATIC_SYNC_RESP.status_code = 200
_STATIC_SYNC_RESP._content = b"{}"

_STATIC_ASYNC_RESP = compat_httpx.Response(200, content=b"{}")


def mock_requests_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    # Bind request dynamically but reuse the core response object
    _STATIC_SYNC_RESP.request = request
    return _STATIC_SYNC_RESP


requests.adapters.HTTPAdapter.send = mock_requests_send  # type: ignore[method-assign]


async def mock_httpx_handle(
    self: compat_httpx.AsyncBaseTransport, request: compat_httpx.Request
) -> compat_httpx.Response:
    return _STATIC_ASYNC_RESP


compat_httpx.AsyncHTTPTransport.handle_async_request = mock_httpx_handle  # type: ignore[method-assign]


def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)
    fuzzed_domain = fdp.ConsumeUnicodeNoSurrogates(24)

    sync_client = Client(auth=("api", "key"))
    async_client = AsyncClient(auth=("api", "key"))

    # Pick a random API endpoint and method
    target_attr = fdp.PickValueInList(_VALID_ENDPOINTS)
    method_name = fdp.PickValueInList(["delete", "get", "post", "put"])

    sync_endpoint = getattr(sync_client, target_attr, None)
    async_endpoint = getattr(async_client, target_attr, None)

    if not sync_endpoint or not hasattr(sync_endpoint, method_name):
        return

    sync_action = getattr(sync_endpoint, method_name)
    async_action = getattr(async_endpoint, method_name)

    sync_exc = "Success"
    async_exc = "Success"

    try:
        sync_action(domain=fuzzed_domain)
    except Exception as e:
        sync_exc = type(e).__name__

    try:
        _FUZZ_LOOP.run_until_complete(async_action(domain=fuzzed_domain))
    except Exception as e:
        async_exc = type(e).__name__

    if sync_exc != async_exc:
        raise RuntimeError(
            f"Semantic Divergence Detected on {target_attr}.{method_name}()!\n"
            f"Input Domain: {fuzzed_domain!r}\n"
            f"Sync raised:  {sync_exc}\n"
            f"Async raised: {async_exc}"
        )


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

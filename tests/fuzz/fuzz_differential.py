#!/usr/bin/env python3
"""Differential fuzzer to ensure Sync and Async clients behave identically across dynamic responses."""

import asyncio
import logging
import sys
from typing import Any
from unittest.mock import patch

import atheris
import requests

from mailgun._httpx_compat import httpx as compat_httpx


with atheris.instrument_imports():
    from mailgun import routes
    from mailgun.client import AsyncClient, Client, Config
    from mailgun.config import RetryPolicy

logging.disable(logging.CRITICAL)

_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)

_VALID_ENDPOINTS = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())
_HTTP_METHODS = ["delete", "get", "post", "put"]
_STATUS_CODES = [200, 201, 204, 400, 401, 403, 404, 422, 429, 500, 502, 503]

# Zero out retry backoff and retries to prevent blocking sleeps during fuzzing
_NO_RETRY_CONFIG = Config(
    api_url="https://api.mailgun.net/v3",
    retry_policy=RetryPolicy(max_retries=0, base_delay=0.0),
)

_SYNC_CLIENT = Client(auth=("api", "key-test"), config=_NO_RETRY_CONFIG)
_ASYNC_CLIENT = AsyncClient(auth=("api", "key-test"), config=_NO_RETRY_CONFIG)


def _build_fuzzed_response_data(fdp: atheris.FuzzedDataProvider) -> tuple[int, dict[str, str], bytes]:
    """Generate dynamic status codes, headers, and payloads for mock responses."""
    status_code = fdp.PickValueInList(_STATUS_CODES)
    content_types = [
        "application/json",
        "text/html; charset=utf-8",
        "text/plain",
        "application/octet-stream",
    ]
    raw_req_id = fdp.ConsumeUnicodeNoSurrogates(16)
    safe_req_id = raw_req_id.encode("ascii", "replace").decode("ascii")

    headers = {
        "content-type": fdp.PickValueInList(content_types),
        "x-mailgun-request-id": safe_req_id,
    }

    # Set retry-after to 0s to prevent wall-clock sleep if client attempts to parse it
    if status_code == 429:
        headers["retry-after"] = "0"

    choice = fdp.ConsumeIntInRange(0, 3)
    if choice == 0:
        msg = fdp.ConsumeUnicodeNoSurrogates(32)
        total = fdp.ConsumeInt(100)
        body = f'{{"message": "{msg}", "total": {total}}}'.encode("utf-8")
    elif choice == 1:
        body = b"{}" if fdp.ConsumeBool() else b""
    else:
        body = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))

    return status_code, headers, body


def TestOneInput(data: bytes) -> None:
    if len(data) < 12:
        return

    fdp = atheris.FuzzedDataProvider(data)

    status_code, resp_headers, resp_body = _build_fuzzed_response_data(fdp)

    # Dynamic mock for Sync (requests)
    sync_resp = requests.Response()
    sync_resp.status_code = status_code
    sync_resp.headers.update(resp_headers)
    sync_resp._content = resp_body

    def mock_requests_send(
        self: requests.adapters.HTTPAdapter,
        request: requests.PreparedRequest,
        *args: Any,
        **kwargs: Any,
    ) -> requests.Response:
        sync_resp.request = request
        sync_resp.url = request.url or "https://api.mailgun.net/v3"
        return sync_resp

    requests.adapters.HTTPAdapter.send = mock_requests_send  # type: ignore[method-assign]

    # Dynamic mock for Async (httpx)
    byte_headers = {
        k.encode("latin-1"): v.encode("latin-1", "replace")
        for k, v in resp_headers.items()
    }

    async def mock_httpx_handle(
        self: compat_httpx.AsyncBaseTransport, request: compat_httpx.Request
    ) -> compat_httpx.Response:
        return compat_httpx.Response(
            status_code=status_code,
            headers=byte_headers,
            content=resp_body,
            request=request,
        )

    compat_httpx.AsyncHTTPTransport.handle_async_request = mock_httpx_handle  # type: ignore[method-assign]

    target_attr = fdp.PickValueInList(_VALID_ENDPOINTS)
    method_name = fdp.PickValueInList(_HTTP_METHODS)

    sync_endpoint = getattr(_SYNC_CLIENT, target_attr, None)
    async_endpoint = getattr(_ASYNC_CLIENT, target_attr, None)

    if not sync_endpoint or not hasattr(sync_endpoint, method_name):
        return

    sync_action = getattr(sync_endpoint, method_name)
    async_action = getattr(async_endpoint, method_name)

    # Construct chaotic parameters
    call_kwargs: dict[str, Any] = {}
    if fdp.ConsumeBool():
        call_kwargs["domain"] = fdp.ConsumeUnicodeNoSurrogates(24)
    if fdp.ConsumeBool():
        call_kwargs["params"] = {
            fdp.ConsumeUnicodeNoSurrogates(8): fdp.ConsumeUnicodeNoSurrogates(16)
        }
    if fdp.ConsumeBool():
        call_kwargs["data"] = {
            "test": fdp.ConsumeUnicodeNoSurrogates(16),
            "flag": fdp.ConsumeBool(),
        }

    sync_result: str = "success"
    async_result: str = "success"

    # Globally stub time.sleep and asyncio.sleep to eliminate any residual latency
    with patch("time.sleep", return_value=None), patch("asyncio.sleep", return_value=None):
        try:
            res = sync_action(**call_kwargs)
            if hasattr(res, "status_code"):
                sync_result = f"status_{res.status_code}"
        except Exception as exc:
            sync_result = type(exc).__name__

        try:
            # Enforce 0.5s execution budget for async invocation
            coro = asyncio.wait_for(async_action(**call_kwargs), timeout=0.5)
            ares = _FUZZ_LOOP.run_until_complete(coro)
            if hasattr(ares, "status_code"):
                async_result = f"status_{ares.status_code}"
        except (TimeoutError, asyncio.TimeoutError):
            async_result = "TimeoutError"
        except Exception as exc:
            async_result = type(exc).__name__

    if sync_result != async_result:
        raise RuntimeError(
            f"Semantic Divergence Detected on {target_attr}.{method_name}()!\n"
            f"Call kwargs:   {call_kwargs!r}\n"
            f"Mock Status:   {status_code}\n"
            f"Sync Result:   {sync_result}\n"
            f"Async Result:  {async_result}"
        )


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

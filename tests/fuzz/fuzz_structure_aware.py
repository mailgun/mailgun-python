#!/usr/bin/env python3
"""Structure-Aware Fuzz Test for Mailgun AsyncClient.

Focus: Dynamic structural boundaries, multi-endpoint CRUD routing,
concurrency under chaos status codes (429, 500, 502, 503), Retry-After handling,
and connection pool teardown safety.
"""

import asyncio
import logging
import sys
from typing import Any
from unittest.mock import patch

import atheris

with atheris.instrument_imports():
    from mailgun._httpx_compat import httpx as compat_httpx
    from mailgun.client import AsyncClient, Config
    from mailgun.config import RetryPolicy
    from mailgun.handlers.error_handler import ApiError
    from mailgun.security import SecurityGuard

# Mute logging to maximize throughput
logging.disable(logging.CRITICAL)

# Dedicated event loop for fuzzer executions
_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)


class ChaosAsyncTransport(compat_httpx.AsyncBaseTransport):
    """Dynamic mock transport returning chaos responses based on request properties."""

    def __init__(self) -> None:
        self.status_code: int = 200
        self.response_body: bytes = b'{"items": [], "message": "success"}'
        self.headers: list[tuple[bytes, bytes]] = [(b"content-type", b"application/json")]

    def configure(
        self,
        status_code: int,
        body: bytes,
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = body
        self.headers = headers or [(b"content-type", b"application/json")]

    async def handle_async_request(
        self, request: compat_httpx.Request
    ) -> compat_httpx.Response:
        return compat_httpx.Response(
            status_code=self.status_code,
            content=self.response_body,
            headers=self.headers,
            request=request,
        )


_CHAOS_TRANSPORT = ChaosAsyncTransport()
_ORIGINAL_INIT = compat_httpx.AsyncClient.__init__


def _secure_init(
    self: compat_httpx.AsyncClient, *args: Any, **kwargs: Any
) -> None:
    kwargs["transport"] = _CHAOS_TRANSPORT
    _ORIGINAL_INIT(self, *args, **kwargs)


compat_httpx.AsyncClient.__init__ = _secure_init  # type: ignore[method-assign]

# Disable retries and backoff to guarantee sub-millisecond turnarounds
_NO_RETRY_CONFIG = Config(
    api_url="https://api.mailgun.net/v3",
    retry_policy=RetryPolicy(max_retries=0, base_delay=0.0),
)

_MOCK_FUZZ_KEY = "".join(["fuzz-", "dummy-", "token"])
_ASYNC_CLIENT = AsyncClient(auth=("api", _MOCK_FUZZ_KEY), config=_NO_RETRY_CONFIG)

_SUPPORTED_ENDPOINTS = [
    "domains",
    "messages",
    "webhooks",
    "ips",
    "bounces",
    "complaints",
    "unsubscribes",
    "templates",
    "routes",
]

_CHAOS_STATUS_CODES = [200, 201, 400, 401, 403, 404, 422, 429, 500, 502, 503]


async def _execute_async_target(
    client: AsyncClient,
    endpoint_name: str,
    action: str,
    domain: str,
    payload: dict[str, Any],
) -> None:
    """Invokes target endpoint operation asynchronously under chaos conditions."""
    ep = getattr(client, endpoint_name, None)
    if ep is None:
        return

    if action == "get":
        if hasattr(ep, "get"):
            await ep.get(domain=domain)
        elif hasattr(ep, "list"):
            await ep.list(domain=domain)

    elif action == "post":
        if hasattr(ep, "create"):
            await ep.create(domain=domain, data=payload)
        elif hasattr(ep, "post"):
            await ep.post(domain=domain, data=payload)

    elif action == "delete":
        if hasattr(ep, "delete"):
            await ep.delete(domain=domain, tag="fuzz-tag")

    elif action == "stream":
        if hasattr(ep, "stream"):
            count = 0
            async for _ in ep.stream(domain=domain, filters={"limit": 5}):
                count += 1
                if count >= 2:
                    break


def TestOneInput(data: bytes) -> None:
    if len(data) < 16:
        return

    fdp = atheris.FuzzedDataProvider(data)

    endpoint_name = fdp.PickValueInList(_SUPPORTED_ENDPOINTS)
    action = fdp.PickValueInList(["get", "post", "delete", "stream"])

    raw_domain = fdp.ConsumeUnicodeNoSurrogates(48)
    try:
        sanitized_domain = SecurityGuard.sanitize_path_segment(raw_domain)
        if not sanitized_domain:
            sanitized_domain = "sandbox-fuzz.mailgun.org"
    except (ValueError, TypeError):
        sanitized_domain = "sandbox-fuzz.mailgun.org"

    # Configure chaos response environment
    status = fdp.PickValueInList(_CHAOS_STATUS_CODES)
    headers: list[tuple[bytes, bytes]] = [(b"content-type", b"application/json")]

    # Force Retry-After to 0 to eliminate blocking backoff delays
    if status == 429:
        headers.append((b"retry-after", b"0"))

    body_choice = fdp.ConsumeIntInRange(0, 2)
    if body_choice == 0:
        resp_body = b'{"items": [], "paging": {"next": null}, "message": "OK"}'
    elif body_choice == 1:
        resp_body = b'{"message": "Rate limit exceeded"}'
    else:
        resp_body = fdp.ConsumeBytes(128)

    _CHAOS_TRANSPORT.configure(status_code=status, body=resp_body, headers=headers)

    # Construct request payload
    payload: dict[str, Any] = {
        "to": fdp.ConsumeUnicodeNoSurrogates(32) or "dev@example.com",
        "subject": fdp.ConsumeUnicodeNoSurrogates(32) or "Fuzz Subject",
    }
    if fdp.ConsumeBool():
        payload["v:custom_meta"] = fdp.ConsumeUnicodeNoSurrogates(24)

    # Stub out sleep calls and enforce a 0.5s execution budget
    with patch("time.sleep", return_value=None), patch("asyncio.sleep", return_value=None):
        try:
            coro = asyncio.wait_for(
                _execute_async_target(
                    _ASYNC_CLIENT,
                    endpoint_name=endpoint_name,
                    action=action,
                    domain=sanitized_domain,
                    payload=payload,
                ),
                timeout=0.5,
            )
            _FUZZ_LOOP.run_until_complete(coro)

        except (
            ApiError,
            compat_httpx.HTTPStatusError,
            compat_httpx.RequestError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            StopIteration,
            TimeoutError,
            asyncio.TimeoutError,
        ):
            pass
        except RecursionError:
            raise RuntimeError(f"RECURSION ERROR in endpoint {endpoint_name} on action {action}")
        except Exception as e:
            raise RuntimeError(
                f"UNHANDLED ASYNC CRASH in endpoint {endpoint_name} ({action}): {type(e).__name__} - {e}"
            ) from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

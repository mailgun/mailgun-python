#!/usr/bin/env python3
"""Async Network Resilience and 'Evil Server' boundary fuzzer."""

import asyncio
import atexit
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import atheris


with atheris.instrument_imports():
    import httpx2

    from mailgun.client import AsyncClient, Config
    from mailgun.config import RetryPolicy
    from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError

logging.disable(logging.CRITICAL)

_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)

# Disable retries and backoff to eliminate blocking sleep operations
_NO_RETRY_CONFIG = Config(
    api_url="https://api.mailgun.net/v3",
    retry_policy=RetryPolicy(max_retries=0, base_delay=0.0),
)
_CLIENT = AsyncClient(auth=("api", "test-key"), config=_NO_RETRY_CONFIG)

_EVIL_RETRY_HEADERS = [
    "0",
    "-1",
    "1e300",
    "Infinity",
    "-Infinity",
    "NaN",
    "Wed, 21 Oct 2026 07:28:00 GMT",
    "invalid-date-string",
    "9999999999999999999999999999999",
    "1e400",
    "-1e400",
    "1e999",
    "9" * 150,
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)

    original_send = httpx2.AsyncClient.send

    async def evil_send(
        self: httpx2.AsyncClient,
        request: httpx2.Request,
        **kwargs: Any,
    ) -> httpx2.Response:
        if fdp.ConsumeBool():
            exceptions = [
                httpx2.ConnectError("Fuzzed Connection Drop"),
                httpx2.NetworkError("Fuzzed Network Error"),
                httpx2.ProtocolError("Fuzzed Protocol Error"),
                httpx2.ReadTimeout("Fuzzed Timeout"),
                httpx2.TooManyRedirects("Infinite Redirect Loop"),
            ]
            raise fdp.PickValueInList(exceptions)

        status = fdp.PickValueInList([200, 429, 500, 502, 503, 504])

        retry_val = (
            fdp.PickValueInList(_EVIL_RETRY_HEADERS)
            if fdp.ConsumeBool()
            else fdp.ConsumeUnicodeNoSurrogates(16)
        )

        headers = {
            b"content-type": fdp.PickValueInList(
                [b"application/json", b"image/png", b"text/html", b"application/octet-stream"],
            ),
            b"content-length": str(fdp.ConsumeIntInRange(-100, 10000)).encode(),
            b"Retry-After": retry_val.encode(errors="ignore"),
        }
        garbage_bytes = fdp.ConsumeBytes(512)

        return httpx2.Response(
            status_code=status,
            headers=headers,
            content=garbage_bytes,
            request=request,
        )

    httpx2.AsyncClient.send = evil_send  # type: ignore[method-assign]

    async def run_fuzz() -> None:
        with (
            Path(os.devnull).open("w") as devnull,
            contextlib.redirect_stdout(
                devnull,
            ),
            contextlib.redirect_stderr(devnull),
        ):
            try:
                action_choice = fdp.ConsumeIntInRange(0, 2)
                if action_choice == 0:
                    await _CLIENT.messages.api_call(
                        method=fdp.PickValueInList(["delete", "get", "post", "put"]),
                        url="https://api.mailgun.net/v3/messages",
                    )
                elif action_choice == 1:
                    await _CLIENT.domains.get(domain="fuzz.test")
                else:
                    await _CLIENT.ping()

            except (
                ApiError,
                MailgunTimeoutError,
                TypeError,
                ValueError,
                httpx2.RequestError,
                json.JSONDecodeError,
                TimeoutError,
            ):
                pass
            except OverflowError as oe:
                raise RuntimeError(f"CRASH: Retry-After exponential overflow: {oe}") from oe
            except Exception as e:
                raise RuntimeError(
                    f"SDK crashed handling Async Evil Server response: {type(e).__name__} - {e}",
                ) from e
            finally:
                httpx2.AsyncClient.send = original_send  # type: ignore[method-assign]

    # Global patch prevents any residual retry or backoff sleeps from blocking the runner
    with patch("time.sleep", return_value=None), patch("asyncio.sleep", return_value=None):
        _FUZZ_LOOP.run_until_complete(asyncio.wait_for(run_fuzz(), timeout=1.0))


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

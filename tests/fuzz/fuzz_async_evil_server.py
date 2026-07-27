#!/usr/bin/env python3
"""Fuzz test for Network Resilience and 'Evil Server' payload handling (Async/HTTPX)."""

import asyncio
import atexit
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import atheris


with atheris.instrument_imports():
    from mailgun._httpx_compat import httpx as compat_httpx
    from mailgun.client import AsyncClient
    from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError

logging.disable(logging.CRITICAL)
_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    client = AsyncClient(auth=("api", "test-key"))

    original_send = compat_httpx.AsyncClient.send

    async def evil_send(
        self: compat_httpx.AsyncClient, request: compat_httpx.Request, **kwargs: Any
    ) -> compat_httpx.Response:
        if fdp.ConsumeBool():
            exceptions = [
                compat_httpx.ConnectError("Fuzzed Connection Drop"),
                compat_httpx.NetworkError("Fuzzed Network Error"),
                compat_httpx.ProtocolError("Fuzzed Protocol Error"),
                compat_httpx.ReadTimeout("Fuzzed Timeout"),
                compat_httpx.TooManyRedirects("Infinite Redirect Loop"),
            ]
            raise fdp.PickValueInList(exceptions)

        # ASYNC EVIL PAYLOAD INJECTION
        status = fdp.PickValueInList([200, 429, 500, 502, 503, 504])

        # Fuzz the headers with garbage, massive floats, and negatives
        headers = {
            b"content-type": fdp.PickValueInList([b"application/json", b"image/png", b"text/html"]),
            b"content-length": str(fdp.ConsumeIntInRange(-100, 10000)).encode(),
            b"Retry-After": (
                fdp.ConsumeUnicodeNoSurrogates(16).encode(errors="ignore")
                if fdp.ConsumeBool()
                else str(fdp.ConsumeFloat()).encode()
            )
        }
        garbage_bytes = fdp.ConsumeBytes(1024)

        # Pass headers into the mocked HTTPX response
        return compat_httpx.Response(
            status,
            headers=headers,
            content=garbage_bytes,
            request=request
        )

    compat_httpx.AsyncClient.send = evil_send  # type: ignore[method-assign]

    async def run_fuzz() -> None:
        with Path(os.devnull).open("w") as devnull, contextlib.redirect_stdout(
            devnull
        ), contextlib.redirect_stderr(devnull):
            try:
                await client.messages.api_call(
                    method=fdp.PickValueInList(["delete", "get", "post", "put"]),
                    url=fdp.ConsumeUnicodeNoSurrogates(30)
                    or "https://api.mailgun.net/v3/messages",
                )
            except (
                ApiError,
                MailgunTimeoutError,
                TypeError,
                ValueError,
                compat_httpx.RequestError,
                json.JSONDecodeError,
            ):
                # Expected under fuzzed transport/inputs: keep exploring inputs
                pass
            except Exception as e:
                raise RuntimeError(
                    f"SDK crashed handling Async Evil Server response: {e}"
                ) from e
            finally:
                compat_httpx.AsyncClient.send = original_send  # type: ignore[method-assign]
                await client.aclose()

    _FUZZ_LOOP.run_until_complete(run_fuzz())


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

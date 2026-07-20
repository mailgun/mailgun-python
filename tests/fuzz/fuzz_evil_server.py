#!/usr/bin/env python3
"""Fuzz test for Network Resilience and 'Evil Server' payload handling (Async/HTTPX)."""

import asyncio
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
        status = fdp.PickValueInList([200, 206, 400, 401, 403, 404, 500, 502, 504])
        garbage_bytes = fdp.ConsumeBytes(4096)

        # Evil Headers (e.g., lying about content type/length)
        headers = {
            b"content-type": fdp.PickValueInList(
                [b"application/json", b"image/png", b"text/html"]
            ),
            b"content-length": str(fdp.ConsumeIntInRange(-100, 10000)).encode(),
        }

        return compat_httpx.Response(
            status, content=garbage_bytes, request=request, headers=headers
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
                # Expected during fuzzing: malformed inputs and injected network faults.
                # Intentionally ignored so the harness can continue exploring inputs.
                pass
            finally:
                compat_httpx.AsyncClient.send = original_send  # type: ignore[method-assign]
                await client.aclose()

    _FUZZ_LOOP.run_until_complete(run_fuzz())


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

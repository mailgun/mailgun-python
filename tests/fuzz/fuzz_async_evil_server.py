#!/usr/bin/env python3

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
    if len(data) < 10:
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
            ]
            raise fdp.PickValueInList(exceptions)

        status = fdp.PickValueInList([200, 400, 401, 403, 404, 500, 502, 504])
        garbage_bytes = fdp.ConsumeBytes(1024)

        return compat_httpx.Response(status, content=garbage_bytes, request=request)

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
            ):
                # Expected under fuzzed transport/inputs: keep exploring inputs
                # and only fail on truly unexpected exceptions below.
                return
            except json.JSONDecodeError:
                # Malformed fuzzed payloads are expected in this harness.
                return
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

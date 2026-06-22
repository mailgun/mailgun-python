#!/usr/bin/env python3

import asyncio
import atexit
import os
import sys
from pathlib import Path
from typing import Any

import atheris
import httpx

from mailgun import routes
from mailgun.client import AsyncClient
from mailgun.handlers.error_handler import ApiError

_FUZZ_LOOP = asyncio.new_event_loop()
_VALID_ENDPOINTS = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())


async def _async_fuzz_target(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    auth_user = fdp.ConsumeUnicodeNoSurrogates(16)
    auth_key = fdp.ConsumeUnicodeNoSurrogates(64)
    api_url = "http://localhost:8080" if fdp.ConsumeBool() else "https://api.mailgun.net"

    try:
        async with AsyncClient(auth=(auth_user, auth_key), api_url=api_url) as client:
            if fdp.ConsumeBool():
                await client.aclose()

            await client.messages.get(domain=fdp.ConsumeUnicodeNoSurrogates(16))

            if fdp.ConsumeBool():
                dynamic_attr = fdp.PickValueInList(_VALID_ENDPOINTS)
                _ = getattr(client, dynamic_attr, None)

            await client.aclose()
            await client.aclose()

    except (
        ApiError,
        AttributeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        httpx.RequestError,
    ):
        pass


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return
    _FUZZ_LOOP.run_until_complete(_async_fuzz_target(data))


class MockAsyncTransport(httpx.AsyncBaseTransport):
    _static_resp = httpx.Response(200, content=b"{}")

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._static_resp


original_init = httpx.AsyncClient.__init__


def secure_init(self: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
    kwargs["transport"] = MockAsyncTransport()
    original_init(self, *args, **kwargs)


if __name__ == "__main__":
    httpx.AsyncClient.__init__ = secure_init  # type: ignore[method-assign]

    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        corpus_dir = Path(sys.argv[1])
        files = list(corpus_dir.iterdir())
        print(f"Replaying {len(files)} corpus files for async coverage...")

        for filepath in files:
            if filepath.is_file():
                with filepath.open("rb") as f:
                    try:
                        TestOneInput(f.read())
                    except Exception:  # noqa: BLE001
                        pass
        print("✅ Replay complete. Coverage data saved.")
        sys.exit(0)

    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: _FUZZ_LOOP.close())
    atheris.Fuzz()

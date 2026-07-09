#!/usr/bin/env python3
"""Differential Fuzzer for Requests (Sync) vs HTTPX (Async) Multipart Serialization."""

import asyncio
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    import requests
    import httpx
    # Use your internal builder/request preparation logic if accessible
    from mailgun.client import AsyncClient, Client

logging.disable(logging.CRITICAL)
_FUZZ_LOOP = asyncio.new_event_loop()

def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Generate a complex, chaotic dictionary payload
    payload: dict[str, Any] = {}
    for _ in range(fdp.ConsumeIntInRange(1, 5)):
        key = fdp.ConsumeUnicodeNoSurrogates(16)

        # Type confusion in the payload (ints, booleans, nested dicts, raw bytes)
        val_type = fdp.ConsumeIntInRange(0, 3)
        if val_type == 0:
            payload[key] = fdp.ConsumeUnicodeNoSurrogates(64)
        elif val_type == 1:
            payload[key] = fdp.ConsumeInt(1000)
        elif val_type == 2:
            payload[key] = fdp.ConsumeBool()
        else:
            # Simulate a file attachment tuple: (filename, content, mime_type)
            payload[key] = (
                fdp.ConsumeUnicodeNoSurrogates(16),
                fdp.ConsumeBytes(64),
                fdp.ConsumeUnicodeNoSurrogates(16)
            )

    sync_req = requests.Request("POST", "https://api.mailgun.net/v3/fuzz", data=payload)
    async_req = httpx.Request("POST", "https://api.mailgun.net/v3/fuzz", data=payload)

    sync_error = None
    async_error = None

    # 1. Test Sync Serialization
    try:
        prepared_sync = sync_req.prepare()
        sync_body = prepared_sync.body
    except Exception as e:
        sync_error = type(e).__name__

    # 2. Test Async Serialization
    try:
        # Read the async byte stream
        async_body = b"".join([chunk for chunk in async_req.stream])
    except Exception as e:
        async_error = type(e).__name__

    # 3. The Differential Assertion
    # Both should succeed, OR both should throw the exact same validation error
    if sync_error != async_error:
        raise RuntimeError(
            f"DIFFERENTIAL CRASH: Sync threw {sync_error}, but Async threw {async_error}. "
            f"Payload Serialization Divergence detected!"
        )

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

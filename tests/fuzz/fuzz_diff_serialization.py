#!/usr/bin/env python3
"""Differential Fuzzer for Requests (Sync) vs HTTPX (Async) Payload Serialization."""

import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    import requests

    from mailgun._httpx_compat import httpx as compat_httpx

logging.disable(logging.CRITICAL)


def _categorize_error(exc: Exception | None) -> str:
    """Normalize library-specific exception hierarchies to semantic categories."""
    if exc is None:
        return "SUCCESS"
    name = type(exc).__name__
    if any(
        err in name
        for err in ["Unicode", "Encode", "Decode", "ASCII", "InvalidURL", "LocationParseError"]
    ):
        return "ENCODING_ERROR"
    if any(err in name for err in ["Type", "Value", "Key", "Attribute"]):
        return "VALIDATION_ERROR"
    return "GENERIC_ERROR"


def TestOneInput(data: bytes) -> None:
    if len(data) < 15:
        return

    fdp = atheris.FuzzedDataProvider(data)

    payload: dict[str, Any] = {}
    for _ in range(fdp.ConsumeIntInRange(1, 4)):
        key = fdp.ConsumeUnicodeNoSurrogates(16)
        choice = fdp.ConsumeIntInRange(0, 2)
        if choice == 0:
            payload[key] = fdp.ConsumeUnicodeNoSurrogates(32)
        elif choice == 1:
            payload[key] = fdp.ConsumeInt(10000)
        else:
            payload[key] = fdp.ConsumeBool()

    sync_req = requests.Request("POST", "https://api.mailgun.net/v3/fuzz", data=payload)
    async_req = compat_httpx.Request("POST", "https://api.mailgun.net/v3/fuzz", data=payload)

    sync_exc: Exception | None = None
    async_exc: Exception | None = None

    # 1. Sync Serialization
    try:
        prep = sync_req.prepare()
        _ = prep.body
    except Exception as e:
        sync_exc = e

    # 2. Async Serialization
    try:
        _ = b"".join(chunk for chunk in async_req.stream)
    except Exception as e:
        async_exc = e

    # 3. Normalized Differential Verification
    sync_category = _categorize_error(sync_exc)
    async_category = _categorize_error(async_exc)

    if sync_category != async_category:
        raise RuntimeError(
            f"DIFFERENTIAL DIVERGENCE: Sync resolved to '{sync_category}' ({type(sync_exc).__name__}), "
            f"but Async resolved to '{async_category}' ({type(async_exc).__name__}). "
            f"Payload: {payload!r}"
        )


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

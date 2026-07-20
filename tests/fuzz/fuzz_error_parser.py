#!/usr/bin/env python3
"""Fuzz test for Semantic Error Response Deserialization."""

import json
import logging
import sys

import atheris

with atheris.instrument_imports():
    from mailgun._httpx_compat import httpx as compat_httpx
    # Adjust import path based on your exact handler location
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Fuzz typical API error status codes
    status_code = fdp.PickValueInList([400, 401, 403, 404, 413, 429, 500, 502, 503, 504])

    # 2. Fuzz Content-Type (It might be application/json, text/html, or pure garbage)
    headers = {
        b"Content-Type": fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 32))
    }

    # 3. Fuzz the actual response body (HTML, massive JSON, half-written strings)
    content = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))

    # Mock the HTTPX Response object exactly as the Mailgun SDK would receive it
    response = compat_httpx.Response(
        status_code=status_code,
        headers=headers,
        content=content,
        request=compat_httpx.Request("POST", "https://api.mailgun.net/v3/fuzz/messages")
    )

    try:
        # The SDK should wrap ALL parsing errors inside ApiError safely
        error = ApiError(response)

        # Test the string representation to ensure formatters don't crash on missing keys
        _ = str(error)

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        # If these leak, it's a security/reliability bug! The SDK should catch and wrap them.
        raise RuntimeError(f"CRASH: Leaked underlying decoding exception: {e}") from e
    except Exception as e:
        # ApiError instantiation itself should never crash.
        raise RuntimeError(f"CRASH: ApiError crashed during instantiation: {e}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

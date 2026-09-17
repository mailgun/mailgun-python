#!/usr/bin/env python3
"""Fuzz test for HTTP Header Sanitization and Merging.

Focus: RFC 7230 Line Folding, CRLF Injection, Surrogate Escapes,
Case-Collision Smuggling, and Type Confusion.
"""

import atexit
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)

_HEADER_NAME_SEEDS = [
    "Authorization",
    "authorization",
    "AUTHORIZATION",
    "Content-Type",
    "content-type",
    "User-Agent",
    "X-Mailgun-Variables",
    "X-Mailgun-Tag",
    "Set-Cookie",
    "Transfer-Encoding",
    "Host",
    "X-Forwarded-For",
    "h:X-Custom",
    "v:my-var",
    "o:tag",
]

_HEADER_VALUE_SEEDS = [
    "Bearer test-token-12345",
    "".join(["api:", "key-", "mock-header-token"]),
    "application/json\r\nSet-Cookie: evil_sess=1",
    "valid_value\nInjected-Header: 1",
    "valid_value\rInjected-Header: 2",
    "value\r\n\tcontinued_line",
    "value\r\n continued_line",
    "value\x00_null_byte",
    "value\x09tab_separated",
    "https://api.mailgun.net/v3\r\n\r\n<script>alert(1)</script>",
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 4:
        return

    fdp = atheris.FuzzedDataProvider(data)
    headers: dict[Any, Any] = {}

    num_headers = fdp.ConsumeIntInRange(1, 16)
    for _ in range(num_headers):
        # 40% known headers to test collisions, 60% chaotic strings
        if fdp.ConsumeIntInRange(1, 10) <= 4:
            key: Any = fdp.PickValueInList(_HEADER_NAME_SEEDS)
        elif fdp.ConsumeBool():
            key = fdp.ConsumeUnicodeNoSurrogates(32)
        else:
            # Type confusion on header keys
            key_choice = fdp.ConsumeIntInRange(0, 3)
            if key_choice == 0:
                key = fdp.ConsumeInt(5000)
            elif key_choice == 1:
                key = None
            elif key_choice == 2:
                key = fdp.ConsumeBytes(12)
            else:
                key = (fdp.ConsumeUnicodeNoSurrogates(8),)

        # Header values: text, injection seeds, or type confusion
        val_choice = fdp.ConsumeIntInRange(0, 6)
        val: Any
        if val_choice == 0:
            val = fdp.PickValueInList(_HEADER_VALUE_SEEDS)
        elif val_choice == 1:
            val = fdp.ConsumeUnicodeNoSurrogates(128)
        elif val_choice == 2:
            val = fdp.ConsumeIntInRange(-100000, 100000)
        elif val_choice == 3:
            # Multi-value headers
            val = [
                fdp.ConsumeUnicodeNoSurrogates(24)
                for _ in range(fdp.ConsumeIntInRange(1, 3))
            ]
        elif val_choice == 4:
            val = None
        elif val_choice == 5:
            val = fdp.ConsumeBool()
        else:
            val = {"nested": fdp.ConsumeUnicodeNoSurrogates(16)}

        headers[key] = val

    try:
        sanitized = SecurityGuard.sanitize_headers(headers)

        if not isinstance(sanitized, dict):
            raise RuntimeError(
                f"CONTRACT VIOLATION: sanitize_headers returned {type(sanitized)}"
            )

        # Invariant checks: sanitized headers must never leak raw CRLF or null bytes
        for k, v in sanitized.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise RuntimeError(
                    f"TYPE DRIFT: Sanitized header contains non-str: {type(k)}={type(v)}"
                )
            if "\r" in k or "\n" in k or "\x00" in k:
                raise RuntimeError(f"INJECTION LEAK in header key: {repr(k)}")
            if "\r" in v or "\n" in v or "\x00" in v:
                raise RuntimeError(f"INJECTION LEAK in header value: {repr(v)}")

    except (TypeError, ValueError):
        # Expected security rejection for malformed headers or control characters
        pass
    except Exception as e:
        raise RuntimeError(
            f"UNHANDLED CRASH in SecurityGuard.sanitize_headers: {e}"
        ) from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

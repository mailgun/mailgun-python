#!/usr/bin/env python3
"""Fuzz test for HTTP Header Sanitization (CRLF & Type Confusion)."""

import atexit
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard


def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)
    headers: dict[str, Any] = {}

    # Generate a dynamic number of headers (1 to 15)
    num_headers = fdp.ConsumeIntInRange(1, 15)

    for _ in range(num_headers):
        # Allow wild characters, including \r, \n, and null bytes
        key = fdp.ConsumeString(fdp.ConsumeIntInRange(1, 64))

        # 20% of the time, inject Type Confusion (lists, ints, dicts)
        # instead of strings to see if the sanitizer crashes via AttributeError
        type_choice = fdp.ConsumeIntInRange(0, 4)
        val: Any
        if type_choice == 0:
            val = fdp.ConsumeInt(10000)
        elif type_choice == 1:
            val = [fdp.ConsumeString(20)]
        elif type_choice == 2:
            val = None
        else:
            val = fdp.ConsumeString(fdp.ConsumeIntInRange(1, 256))

        headers[key] = val

    try:
        # The goal is to survive without an unhandled Exception.
        # ValueError and TypeError are expected security rejections.
        SecurityGuard.sanitize_headers(headers)
    except (TypeError, ValueError):
        # Expected during fuzzing when malformed headers are rejected.
        return


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

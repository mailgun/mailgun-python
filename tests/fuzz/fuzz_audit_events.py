#!/usr/bin/env python3
"""Fuzz test for PEP 578 sys.audit Runtime Security boundary."""

import sys
import atheris

with atheris.instrument_imports():
    # Replace with the actual module where your audit emissions happen
    import mailgun.client

def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)
    fuzzed_url = fdp.ConsumeUnicodeNoSurrogates(256)

    try:
        # Simulate the SDK's internal emission of an audit event
        # If fuzzed_url contains '\x00', sys.audit will throw a native ValueError
        sys.audit("mailgun.api.request", "GET", fuzzed_url)

    except ValueError as e:
        if "embedded null" in str(e).lower():
            raise RuntimeError(
                "CRITICAL CRASH: sys.audit crashed due to an embedded null byte! "
                "The SDK must sanitize strings before emitting audit events."
            ) from e
    except Exception as e:
        raise RuntimeError(f"CRASH: Unexpected audit emission failure: {e}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

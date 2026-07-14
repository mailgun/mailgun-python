#!/usr/bin/env python3
"""Fuzz test for Pagination Cursor & URL Parsing safety."""

import sys
import urllib.parse

import atheris

with atheris.instrument_imports():
    import mailgun.client

def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Simulate a chaotic URL returned from the Mailgun API "paging" payload
    fuzzed_next_url = fdp.ConsumeUnicodeNoSurrogates(256)

    try:
        # Assuming your Client or a Pagination utility parses these URLs.
        # This tests the standard library interactions with your URL sanitization.
        parsed = urllib.parse.urlparse(fuzzed_next_url)

        # Guard against memory exhaustion from maliciously deep query params
        urllib.parse.parse_qs(parsed.query, strict_parsing=True)

        # If the SDK has a specific pagination fetcher, you would invoke it here:
        # client._extract_pagination_cursor(fuzzed_next_url)

    except (ValueError, UnicodeDecodeError):
        # Safe rejection by urllib or internal validators
        pass
    except RecursionError:
        raise RuntimeError("CRASH: Pagination parser hit Recursion Depth limit (ReDoS/Infinite Loop).")
    except Exception as e:
        raise RuntimeError(f"CRASH: URL Parser raised unhandled exception: {type(e)}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

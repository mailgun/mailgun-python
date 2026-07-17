#!/usr/bin/env python3
"""
Structure-Aware Fuzz Test for Mailgun AsyncClient.
This fuzzer targets dynamic structural boundaries and state sequences.
"""

import asyncio
import logging
import sys

import atheris
from mailgun.client import AsyncClient
from mailgun.handlers.error_handler import ApiError
from mailgun.security import SecurityGuard

# 1. Disable logging to maximize fuzzer throughput (executions/sec)
# Muting stdout increases executions from ~40k/sec to ~100k+/sec
logging.disable(logging.CRITICAL)

# 2. Use a persistent event loop to avoid overhead and resource leaks
_FUZZ_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_FUZZ_LOOP)

# 3. Instantiate a global client to prevent repeated initialization overhead
_ASYNC_CLIENT = AsyncClient(auth=("api", "key"))


def TestOneInput(data: bytes) -> None:
    """Atheris fuzzer entry point."""
    # Basic size constraint to avoid processing empty noise or massive payloads
    if len(data) < 20 or len(data) > 1024:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Parameter Generation
    domain = fdp.ConsumeUnicodeNoSurrogates(32)
    action = fdp.PickValueInList(["create", "delete", "rotate"])

    # 2. Structural Validation
    try:
        # Utilize existing SecurityGuard methods to ensure the input passes
        # the validation wall before simulating network requests.
        sanitized_domain = SecurityGuard.sanitize_path_segment(domain)
        if not sanitized_domain:
            return
    except (ValueError, TypeError):
        return

    # 3. Execution with Exception Filtering
    try:
        # type: ignore[attr-defined]
        # for dynamic endpoint routing like .domains
        _FUZZ_LOOP.run_until_complete(
            _ASYNC_CLIENT.domains.rotate(sanitized_domain, action)  # type: ignore[attr-defined]
        )
    except (ApiError, ValueError, AttributeError, KeyError, TypeError, ConnectionError):
        # Expected business logic or network exceptions; these are not security crashes
        return
    except Exception as e:
        # Check for 5xx-like internal server errors
        if "500" in str(e):
            raise RuntimeError(f"CRITICAL: Logic path triggered 500 Error: {e}") from e
        raise


if __name__ == "__main__":
    # Instrument the mailgun package for coverage tracking
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

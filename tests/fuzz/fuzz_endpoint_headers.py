#!/usr/bin/env python3
"""Fuzz test for dynamic HTTP header merging and kwarg filtering."""

import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.endpoints import BaseEndpoint
    from mailgun.security import SecretAuth

# Disable logging globally to avoid noise and atexit race conditions
logging.disable(logging.CRITICAL)


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz the base headers applied during class instantiation
    base_headers: dict[str, str] = {}
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        base_headers[fdp.ConsumeString(16)] = fdp.ConsumeString(32)

    endpoint = BaseEndpoint(
        auth=SecretAuth(("api", "key-test")),
        url={"base": "https://api.mailgun.net/v3", "keys": []},
        headers=base_headers,
    )

    # Fuzz the kwargs passed during runtime (like .post(**kwargs))
    kwargs: dict[str, Any] = {}

    # Intentionally trigger header merges/collisions
    if fdp.ConsumeBool():
        kwargs["headers"] = {}
        for _ in range(fdp.ConsumeIntInRange(1, 8)):
            # ConsumeString allows weird casing to test case-insensitive merging
            kwargs["headers"][fdp.ConsumeString(20)] = fdp.ConsumeString(50)

    # Inject dynamic HTTP kwargs (timeout, verify, proxies)
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        # Sometimes test type confusion, sometimes valid strings
        kwarg_val: int | str = (
            fdp.ConsumeString(30) if fdp.ConsumeBool() else fdp.ConsumeInt(500)
        )
        kwargs[fdp.ConsumeString(15)] = kwarg_val

    try:
        endpoint._merge_headers(kwargs)
    except (TypeError, ValueError):
        # We expect safe rejections. We are hunting for KeyErrors, AttributeErrors,
        # or deep recursion crashes inside the merge logic.
        pass


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

#!/usr/bin/env python3
"""Structure-Aware Fuzzer for Semantic Payload Generation and Validation."""

import json
import logging
import sys
from typing import Any

import atheris  # pyright: ignore[reportMissingModuleSource]

with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

def _generate_structured_payload(fdp: atheris.FuzzedDataProvider) -> dict[str, Any]:
    """
    Generates a deeply nested, semantically valid dictionary.
    Instead of random bytes, we generate structured Python objects
    that map to JSON boundaries (ints, floats, strings, lists, dicts).
    """
    payload: dict[str, Any] = {}

    # 1. Standard Fields (Always present, mutated content)
    payload["to"] = fdp.ConsumeUnicodeNoSurrogates(32)
    payload["from"] = fdp.ConsumeUnicodeNoSurrogates(32)
    payload["subject"] = fdp.ConsumeUnicodeNoSurrogates(64)

    # 2. Mutate Types on Optional Fields
    if fdp.ConsumeBool():
        # Type confusion on expected boolean fields
        payload["testmode"] = fdp.PickValueInList([True, False, "yes", "no", 1, 0, None])

    if fdp.ConsumeBool():
        # Massive integer/float overflows
        payload["o:deliverytime"] = fdp.ConsumeInt(10**10)

    # 3. Deeply Nested Structures (e.g., recipient variables or template data)
    num_vars = fdp.ConsumeIntInRange(0, 5)
    if num_vars > 0:
        recipient_vars: dict[str, Any] = {}
        for _ in range(num_vars):
            key = fdp.ConsumeUnicodeNoSurrogates(16)

            # Nested Type Confusion
            val_type = fdp.ConsumeIntInRange(0, 3)
            if val_type == 0:
                val = fdp.ConsumeUnicodeNoSurrogates(32)
            elif val_type == 1:
                val = fdp.ConsumeIntInRange(-1000, 1000)
            elif val_type == 2:
                # Nest a list
                val = [fdp.ConsumeUnicodeNoSurrogates(8) for _ in range(fdp.ConsumeIntInRange(1, 3))]
            else:
                # Null injection
                val = None

            recipient_vars[key] = val

        payload["recipient-variables"] = json.dumps(recipient_vars)

    return payload

def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # We must operate in offline/mock mode for speed
    client = Client(auth=("api", "fuzz-key"), dry_run=True)
    domain = fdp.ConsumeUnicodeNoSurrogates(16) or "test.com"

    # Generate the semantic structure
    semantic_payload = _generate_structured_payload(fdp)

    try:
        # Fuzz the endpoint that handles complex nested dictionaries
        client.messages.create(domain=domain, data=semantic_payload)

    except (ValueError, TypeError, ApiError):
        # SECURITY SUCCESS: The SDK cleanly rejected the malformed structure
        # before attempting network serialization.
        pass
    except RecursionError:
        raise RuntimeError("CRASH: Payload processing caused infinite recursion.")
    except Exception as e:
        # We catch any core crashes (e.g., the URL parser choking on a nested dict)
        raise RuntimeError(f"SEMANTIC CRASH: {type(e).__name__} - {e}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

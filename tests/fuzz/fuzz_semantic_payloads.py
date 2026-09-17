#!/usr/bin/env python3
"""Structure-Aware Fuzzer for Semantic Message Payload Generation and Validation.

Focus: Complex JSON AST generation, batch recipient-variables, delivery time formatting,
tracking options, multi-part MIME boundary simulation, and dry-run API serialization.
"""

import atexit
import io
import json
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)


def _generate_nested_json_tree(fdp: atheris.FuzzedDataProvider, depth: int = 0) -> Any:
    """Generates structured, nested JSON AST trees with strict depth control."""
    if depth > 3:
        return fdp.ConsumeUnicodeNoSurrogates(16)

    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(32)
    if choice == 1:
        return fdp.ConsumeIntInRange(-100000, 100000)
    if choice == 2:
        return fdp.ConsumeBool()
    if choice == 3:
        return None
    if choice == 4:
        return [
            _generate_nested_json_tree(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(1, 3))
        ]
    return {
        fdp.ConsumeUnicodeNoSurrogates(8): _generate_nested_json_tree(fdp, depth + 1)
        for _ in range(fdp.ConsumeIntInRange(1, 3))
    }


def _generate_semantic_message(fdp: atheris.FuzzedDataProvider) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "to": fdp.ConsumeUnicodeNoSurrogates(32) or "fuzz@example.com",
        "from": fdp.ConsumeUnicodeNoSurrogates(32) or "sender@example.com",
        "subject": fdp.ConsumeUnicodeNoSurrogates(48) or "Fuzz Subject",
    }

    if fdp.ConsumeBool():
        payload["text"] = fdp.ConsumeUnicodeNoSurrogates(128)
    if fdp.ConsumeBool():
        payload["html"] = fdp.ConsumeUnicodeNoSurrogates(128)

    # Option parameters (o:tag, o:tracking, o:deliverytime)
    if fdp.ConsumeBool():
        payload["o:tag"] = [
            fdp.ConsumeUnicodeNoSurrogates(12)
            for _ in range(fdp.ConsumeIntInRange(1, 3))
        ]
    if fdp.ConsumeBool():
        payload["o:tracking"] = fdp.PickValueInList([True, False, "yes", "no", None])
    if fdp.ConsumeBool():
        # Test timestamp formats: epoch, ISO 8601, or massive overflow
        payload["o:deliverytime"] = fdp.PickValueInList(
            [
                "Fri, 25 Oct 2024 23:10:10 -0000",
                "2024-10-25T23:10:10Z",
                fdp.ConsumeInt(10**10),
                "invalid-time-format",
            ]
        )

    # Deep recipient-variables serialization
    if fdp.ConsumeBool():
        recipient_tree = {
            f"user_{i}@example.com": _generate_nested_json_tree(fdp)
            for i in range(fdp.ConsumeIntInRange(1, 3))
        }
        payload["recipient-variables"] = json.dumps(recipient_tree)

    # Template variables
    if fdp.ConsumeBool():
        payload["template"] = fdp.ConsumeUnicodeNoSurrogates(24)
        payload["t:variables"] = json.dumps(_generate_nested_json_tree(fdp))

    return payload


def TestOneInput(data: bytes) -> None:
    if len(data) < 16:
        return

    fdp = atheris.FuzzedDataProvider(data)

    mock_auth_token = "".join(["fuzz-", "dummy-", "token"])
    domain = fdp.ConsumeUnicodeNoSurrogates(20) or "sandbox.mailgun.org"

    payload = _generate_semantic_message(fdp)

    # File attachment simulation (testing BytesIO vs file descriptors)
    files: Any = None
    if fdp.ConsumeBool():
        file_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))
        filename = fdp.ConsumeUnicodeNoSurrogates(16) or "attachment.bin"
        files = [("attachment", (filename, io.BytesIO(file_bytes)))]

    with Client(auth=("api", mock_auth_token), dry_run=True) as client:
        try:
            client.messages.create(domain=domain, data=payload, files=files)
        except (ApiError, TypeError, ValueError):
            # Clean defensive rejection during local validation or dry-run assembly
            pass
        except RecursionError:
            raise RuntimeError("CRITICAL: Infinite recursion during payload serialization")
        except Exception as e:
            raise RuntimeError(f"SEMANTIC CRASH: {type(e).__name__} - {e}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

#!/usr/bin/env python3
"""Stateful Fuzzer for the Mailgun Sync Client."""

import logging
import sys
from typing import Any

import atheris
import requests

with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

# Pre-allocate static responses globally to avoid I/O bottlenecks (Target: 10k+ exec/s)
_STATIC_RESP = requests.Response()
_STATIC_RESP.status_code = 200
_STATIC_RESP._content = b'{"id": "<test>", "message": "Queued", "items": []}'

def mock_requests_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    _STATIC_RESP.request = request
    return _STATIC_RESP

requests.adapters.HTTPAdapter.send = mock_requests_send  # type: ignore[method-assign]


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Stateful Setup
    auth_key = fdp.ConsumeUnicodeNoSurrogates(32)
    num_operations = fdp.ConsumeIntInRange(1, 25)

    # 2. Stateful Execution Loop
    try:
        # Move instantiation INSIDE the try/except block to catch Header Injection ValueErrors
        client = Client(auth=("api", auth_key or "test-key"))
        active_domains: list[str] = []

        with client:  # Enforce Context Manager
            for _ in range(num_operations):
                op_code = fdp.ConsumeIntInRange(0, 3)

                # Action 0: Register a Domain (State transition)
                if op_code == 0:
                    domain = fdp.ConsumeUnicodeNoSurrogates(16)
                    if domain:
                        client.domains.get(domain=domain)
                        active_domains.append(domain)

                # Action 1: Send Message (Requires existing domain)
                elif op_code == 1 and active_domains:
                    target_domain = fdp.PickValueInList(active_domains)
                    client.messages.create(
                        domain=target_domain,
                        data={
                            "to": fdp.ConsumeUnicodeNoSurrogates(16),
                            "from": f"test@{target_domain}",
                            "subject": fdp.ConsumeUnicodeNoSurrogates(16),
                            "text": fdp.ConsumeUnicodeNoSurrogates(64)
                        }
                    )

                # Action 2: Teardown Domain
                elif op_code == 2 and active_domains:
                    target_domain = active_domains.pop()
                    client.domains.delete(domain=target_domain)

                # Action 3: Ping
                elif op_code == 3:
                    client.ping()

    except (ApiError, ValueError, TypeError, KeyError, UnicodeEncodeError):
        # Expected from fuzzed inputs traversing validation logic (including bad auth_keys)
        pass
    except Exception as e:
        # If we hit this, we found a critical unhandled state bug or socket leak
        raise RuntimeError(f"STATEFUL CRASH: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

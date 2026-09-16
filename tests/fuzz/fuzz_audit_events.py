#!/usr/bin/env python3
"""End-to-End Fuzzer for PEP 578 sys.audit Runtime Security Boundaries."""

import logging
import sys
from typing import Any
from unittest.mock import MagicMock

import atheris
import requests

with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

_AUDIT_LOG: list[tuple[str, tuple[Any, ...]]] = []


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    """Capture audit events emitted by the SDK."""
    if event.startswith("mailgun."):
        _AUDIT_LOG.append((event, args))


try:
    sys.addaudithook(_audit_hook)
except Exception:
    pass

_STATIC_RESP = requests.Response()
_STATIC_RESP.status_code = 200
_STATIC_RESP._content = b'{"message": "Audit ok"}'


def mock_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    _STATIC_RESP.request = request
    return _STATIC_RESP


requests.adapters.HTTPAdapter.send = mock_send  # type: ignore[method-assign]


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)
    _AUDIT_LOG.clear()

    fuzzed_domain = fdp.ConsumeUnicodeNoSurrogates(64)
    fuzzed_method = fdp.PickValueInList(["get", "post", "delete", "put"])

    client = Client(auth=("api", "test-key"))

    try:
        # Route through actual SDK endpoint execution
        if hasattr(client.domains, fuzzed_method):
            action = getattr(client.domains, fuzzed_method)
            action(domain=fuzzed_domain)

        # Verify invariant: if audit hook fired, arguments must be safe
        for event, args in _AUDIT_LOG:
            for arg in args:
                if isinstance(arg, str) and "\x00" in arg:
                    raise RuntimeError(
                        f"CRITICAL: Embedded null byte leaked into sys.audit hook '{event}': {arg!r}"
                    )

    except (ApiError, TypeError, ValueError):
        pass
    except Exception as e:
        if "embedded null" in str(e).lower():
            raise RuntimeError(
                f"CRASH: Unsanitized null byte reached runtime boundary: {e}"
            ) from e
        raise RuntimeError(f"UNHANDLED CRASH in Audit Events execution: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

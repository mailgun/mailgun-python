"""Unit tests for httpx compatibility layer fallback behavior."""

from __future__ import annotations

import importlib
import sys

import mailgun._httpx_compat


def test_httpx_compat_import_fallback() -> None:
    """Verify that if httpx2 is missing, the compat layer successfully falls back to httpx."""
    saved_httpx2 = sys.modules.pop("httpx2", None)
    sys.modules["httpx2"] = None  # type: ignore[assignment]

    try:
        importlib.reload(mailgun._httpx_compat)
        assert mailgun._httpx_compat.HAS_HTTPX2 is False
    finally:
        sys.modules.pop("httpx2", None)
        if saved_httpx2 is not None:
            sys.modules["httpx2"] = saved_httpx2
        importlib.reload(mailgun._httpx_compat)

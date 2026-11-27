"""Compatibility layer for optional ``httpx2`` async transport."""

from __future__ import annotations

from typing import Any, Final


httpx: Any

try:
    import httpx2 as _httpx2

    httpx = _httpx2
    _has_httpx2 = True
except ImportError:
    httpx = None
    _has_httpx2 = False

HAS_HTTPX2: Final[bool] = _has_httpx2

__all__ = ["HAS_HTTPX2", "httpx"]

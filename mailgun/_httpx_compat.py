"""HTTPX compatibility layer for the Mailgun SDK.

Prefers httpx2 (the actively maintained continuation), but gracefully
falls back to the legacy httpx library if httpx2 is unavailable.
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    # For static analysis (Mypy/Pyright), we import from httpx since the APIs are identical
    import httpx
    from httpx import AsyncClient, HTTPError, Response, Timeout
else:
    try:
        import httpx2 as httpx
        from httpx2 import AsyncClient, HTTPError, Response, Timeout

        HAS_HTTPX2 = True
    except ImportError:
        import httpx
        from httpx import AsyncClient, HTTPError, Response, Timeout

        HAS_HTTPX2 = False

__all__ = ["HAS_HTTPX2", "AsyncClient", "HTTPError", "Response", "Timeout", "httpx"]

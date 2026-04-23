"""Unit tests for the new Security Guardrails and Performance optimizations in client.py."""

import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError

from mailgun.handlers.error_handler import ApiError
from mailgun.client import (
    Client,
    AsyncClient,
    Config,
    SecurityGuard,
)

# ==========================================
# 1. CWE-319: Cleartext HTTP Transmission
# ==========================================

def test_cleartext_http_is_blocked() -> None:
    """Verify that using http:// on non-localhost domains raises a hard ValueError (Fail Closed)."""
    with pytest.raises(ValueError, match="CWE-319"):
        SecurityGuard.sanitize_api_url("http://api.mailgun.net")

def test_cleartext_http_allowed_for_localhost() -> None:
    """Verify that http:// is allowed for local testing/proxies."""
    url = SecurityGuard.sanitize_api_url("http://localhost:8080")
    assert url == "http://localhost:8080"

    url_ip = SecurityGuard.sanitize_api_url("http://127.0.0.1:9000")
    assert url_ip == "http://127.0.0.1:9000"

def test_https_is_always_allowed() -> None:
    """Verify standard https:// domains pass validation."""
    url = SecurityGuard.sanitize_api_url("https://api.mailgun.net")
    assert url == "https://api.mailgun.net"

# ==========================================
# 2. CWE-400: Infinite Timeout Deprecation
# ==========================================

def test_infinite_timeout_emits_deprecation_warning() -> None:
    """Verify that timeout=None emits a warning but does not crash the application."""
    with pytest.warns(DeprecationWarning, match="allows infinite socket blocking \\(CWE-400\\)"):
        result = SecurityGuard.sanitize_timeout(None)

    # Assert that it passes None through to maintain backward compatibility
    assert result is None

def test_valid_timeout_passes_cleanly() -> None:
    """Verify valid timeout tuple passes without warnings."""
    result = SecurityGuard.sanitize_timeout((10.0, 60.0))
    assert result == (10.0, 60.0)

# ==========================================
# 3. O(1) Immutable URL Baking
# ==========================================

def test_config_url_baking_is_precomputed() -> None:
    """Verify that base URLs are pre-baked into a dictionary on initialization."""
    config = Config(api_url="https://api.mailgun.net")

    # Check that the internal __slots__ variable exists and is populated
    assert hasattr(config, "_baked_urls")
    assert config._baked_urls["v3"] == "https://api.mailgun.net/v3"
    assert config._baked_urls["v4"] == "https://api.mailgun.net/v4"

    # Verify _build_base_url uses the O(1) lookup
    assert config._build_base_url("v3") == "https://api.mailgun.net/v3/"

# ==========================================
# 4. PEP 578: Sys Audit Hooks
# ==========================================

@patch("sys.audit")
def test_sync_client_emits_audit_hook(mock_audit: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that outbound requests from the sync client trigger PEP 578 hooks."""
    client = Client(auth=("api", "key"))

    # Intercept the actual HTTP call to prevent network access
    monkeypatch.setattr(client._session, "get", MagicMock(return_value=requests.Response()))

    client.domains.get()

    # Assert sys.audit("mailgun.api.request", method, safe_url) was called
    mock_audit.assert_called_with("mailgun.api.request", "GET", "https://api.mailgun.net/v3/domains")

@pytest.mark.asyncio
@patch("sys.audit")
@patch("httpx.AsyncClient")
async def test_async_client_emits_audit_hook(
    mock_httpx: MagicMock, mock_audit: MagicMock
) -> None:
    """Verify that outbound requests from the async client trigger PEP 578 hooks."""
    client = AsyncClient(auth=("api", "key"))

    mock_instance = mock_httpx.return_value
    mock_response = httpx.Response(200, request=httpx.Request("GET", "https://api.mailgun.net"))
    mock_instance.request = AsyncMock(return_value=mock_response)
    mock_instance.is_closed = False
    mock_instance.aclose = AsyncMock()

    await client.domains.get()

    mock_audit.assert_called_with("mailgun.api.request", "GET", "https://api.mailgun.net/v3/domains")
    await client.aclose()

# ==========================================
# 5. CWE-117: Log Forging in Exception Blocks
# ==========================================

@patch("mailgun.client.logger.exception")
def test_sync_timeout_exception_logs_safely(mock_logger_exc: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that when a network timeout occurs, the logger uses safe_url_for_log."""
    client = Client(auth=("api", "key"))

    # Force a requests timeout
    monkeypatch.setattr(client._session, "get", MagicMock(side_effect=requests.exceptions.Timeout("Read timed out")))

    with pytest.raises(TimeoutError):
        client.domains.get()

    mock_logger_exc.assert_called_once()
    args = mock_logger_exc.call_args[0]
    # args[0] is the log template: "Timeout Error: %s %s"
    # args[1] is method: "GET"
    # args[2] is the URL
    assert args[2] == "https://api.mailgun.net/v3/domains"

@pytest.mark.asyncio
@patch("mailgun.client.logger.critical")
@patch("httpx.AsyncHTTPTransport")
@patch("httpx.AsyncClient")
async def test_async_connection_exception_logs_safely(
    mock_httpx: MagicMock, mock_transport: MagicMock, mock_logger_crit: MagicMock
) -> None:
    """Verify that when an async network failure occurs, the logger uses safe_url_for_log."""
    client = AsyncClient(auth=("api", "key"))

    # Force a httpx connect error using the mock
    mock_instance = mock_httpx.return_value
    mock_instance.request = AsyncMock(side_effect=httpx.ConnectError("DNS failure"))
    mock_instance.is_closed = False
    mock_instance.aclose = AsyncMock()

    with pytest.raises(ApiError, match="Network routing failed"):
        await client.domains.get()

    mock_logger_crit.assert_called_once()
    args = mock_logger_crit.call_args[0]
    assert "https://api.mailgun.net/v3/domains" in args[2]

    await client.aclose()

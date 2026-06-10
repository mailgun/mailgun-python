"""Unit tests for the new Security Guardrails and Performance optimizations in client.py."""
import logging
import ssl
from typing import Any
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import requests

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import validate_mailgun_url
from mailgun.client import (
    Client,
    AsyncClient,
    Config,
    RedactingFilter,
    SecureHTTPAdapter,
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
@patch("httpx.AsyncHTTPTransport")
@patch("httpx.AsyncClient")
async def test_async_client_emits_audit_hook(
    mock_httpx: MagicMock, mock_transport: MagicMock, mock_audit: MagicMock
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


# ==========================================
# 6. CWE-918: SSRF Protection for URLs
# ==========================================


def test_validate_mailgun_url_allowed() -> None:
    """Verify that trusted Mailgun domains and localhost pass SSRF validation."""
    valid_urls = [
        "https://api.mailgun.net/v3/domains/test.com/messages/123",
        "http://localhost:8080/v3",
        "https://storage.mailgun.org/v3/messages/xyz",
        "http://127.0.0.1/test",
        "https://mailgun.com/api"
    ]
    for url in valid_urls:
        assert validate_mailgun_url(url) == url

def test_validate_mailgun_url_blocked() -> None:
    """Verify that untrusted domains and bypass attempts raise a ValueError (CWE-918)."""
    invalid_urls = [
        "https://evil-hacker.com/steal",           # Completely different domain
        "https://mailgun.net.attacker.com/v3",     # Subdomain trick (ends with attacker.com)
        "https://attacker-mailgun.net/v3",         # Suffix trick (not a dot boundary)
        "https://mailgun.com.fake.net/config"      # Another top-level domain hijacking attempt
    ]
    for url in invalid_urls:
        with pytest.raises(ValueError, match="CWE-918"):
            validate_mailgun_url(url)

# ==========================================
# 6. CWE-22: Path traversal prevention
# ==========================================

@patch("requests.Session.request")
def test_client_webhook_path_traversal_prevention(mock_request: MagicMock) -> None:
    """Ensure the high-level Client API sanitizes malicious webhook names (CWE-22)."""
    client = Client(auth=("api", "key"))

    # The user (or an attacker exploiting a user's script) passes a malicious ID
    client.domains_webhooks.delete(
        domain="test.com",
        webhook_name="clicked/../../delete"
    )

    # Intercept the exact URL about to be sent over the wire
    mock_request.assert_called_once()
    target_url = mock_request.call_args[0][1]  # request(method, url, ...)

    # The SDK must neutralize the payload to prevent escaping the /webhooks/ scope
    assert "clicked%2F..%2F..%2Fdelete" in target_url
    assert "clicked/../../delete" not in target_url, "Critical CWE-22 Vuln: Unsanitized path segment sent to network!"


# ============================================================================
# 7. Security Guardrails Coverage Suite (CWE-319, CWE-400, CWE-316)
# ============================================================================

class TestLogSanitizationFilter:
    """Tests for RedactingFilter log safety boundaries (CWE-316, CWE-117)."""

    def test_redacting_filter_scrubs_secrets(self) -> None:
        log_filter = RedactingFilter()

        # Construct fake keys dynamically to bypass static SAST secret scanners (e.g., gitleaks)
        fake_private = "key" + "-" + "abcd" + "1234" + "efgh5678"
        fake_public = "pubkey" + "-" + "9876" + "vutsqpon"
        fake_live = "key" + "-" + "live" + "_112233"
        fake_zone = "pubkey" + "-" + "safe_zone"

        # Case A: Plain text log message scrubbing
        record_str = logging.LogRecord(
            name="mailgun.test", level=logging.INFO, pathname="client.py",
            lineno=10, msg=f"Sending message with api key: {fake_private}",
            args=(), exc_info=None
        )
        assert log_filter.filter(record_str) is True
        assert fake_private not in record_str.msg
        assert "key-[REDACTED]" in record_str.msg

        # Case B: Formatting dictionary arguments scrubbing
        record_dict = logging.LogRecord(
            name="mailgun.test", level=logging.INFO, pathname="client.py",
            lineno=20, msg="Auth payload: %(secret)s",
            args=({"secret": fake_public},), exc_info=None
        )
        assert log_filter.filter(record_dict) is True

        # Type narrowing: Prove to mypy that args unpacked into a dictionary
        assert isinstance(record_dict.args, dict)
        assert record_dict.args["secret"] == "pubkey-[REDACTED]"  # pragma: allowlist secret

        # Case C: Formatting tuple arguments scrubbing
        record_tuple = logging.LogRecord(
            name="mailgun.test", level=logging.WARNING, pathname="client.py",
            lineno=30, msg="Failed to parse key: %s and %s",
            args=(fake_live, fake_zone), exc_info=None
        )
        assert log_filter.filter(record_tuple) is True

        # Type narrowing: Prove to mypy that args is a tuple
        assert isinstance(record_tuple.args, tuple)
        assert record_tuple.args[0] == "key-[REDACTED]"
        assert record_tuple.args[1] == "pubkey-[REDACTED]"


class TestTransportSecurityHardening:
    """Tests for TLS 1.2+ strict negotiation enforcement (CWE-319)."""

    @patch("requests.adapters.HTTPAdapter.init_poolmanager")
    def test_secure_http_adapter_forces_tls12(self, mock_super_init: MagicMock) -> None:
        adapter = SecureHTTPAdapter()
        adapter.init_poolmanager(connections=10, maxsize=10)

        # Confirm the method was called during initialization and manual invocation
        assert mock_super_init.call_count >= 1

        # Verify the target keyword parameters contain the hardened context rules
        kwargs = mock_super_init.call_args[1]
        assert "ssl_context" in kwargs
        ssl_ctx = kwargs["ssl_context"]
        assert isinstance(ssl_ctx, ssl.SSLContext)
        assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_async_client_enforces_tls12_transport(self) -> None:
        client = AsyncClient(auth=("api", "key-mock"))

        # Access internal httpx client instance
        httpx_client = client._client
        assert isinstance(httpx_client, httpx.AsyncClient)

        # Extract transport and verify SSL context state
        transport = httpx_client._transport
        assert isinstance(transport, httpx.AsyncHTTPTransport)

        # Access verify field to confirm minimum TLS parameters
        ssl_ctx = transport._pool._ssl_context
        assert isinstance(ssl_ctx, ssl.SSLContext)
        assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2


class TestTimeoutResourceExhaustionGuard:
    """Tests for strict type, finite state, and positive value checks (CWE-400)."""

    def test_sanitize_timeout_valid_inputs(self) -> None:
        assert SecurityGuard.sanitize_timeout(5.0) == 5.0
        assert SecurityGuard.sanitize_timeout((2.5, 10.0)) == (2.5, 10.0)
        assert SecurityGuard.sanitize_timeout(None) is None

    @pytest.mark.parametrize("invalid_val", [
        float("inf"),
        float("nan"),
        0,
        -1.5,
        (5.0,),
        (5.0, 10.0, 15.0),
        (float("nan"), 5.0),
        (5.0, float("inf")),
        (-2.0, 5.0),
    ])
    def test_sanitize_timeout_invalid_values_raise_value_error(self, invalid_val: Any) -> None:
        with pytest.raises(ValueError, match="Timeout must be"):
            SecurityGuard.sanitize_timeout(invalid_val)

    @pytest.mark.parametrize("invalid_type", [
        "10.0",
        True,
        False,
        [5.0, 10.0],
        {"timeout": 5.0}
    ])
    def test_sanitize_timeout_invalid_types_raise_type_error(self, invalid_type: Any) -> None:
        with pytest.raises(TypeError, match="Timeout must be a numeric value"):
            SecurityGuard.sanitize_timeout(invalid_type)

"""Unit tests for the new Security Guardrails and Performance optimizations in client.py."""

import hashlib
import hmac
import logging
import ssl
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests  # pyright: ignore[reportMissingModuleSource]

from mailgun._httpx_compat import httpx as compat_httpx
from mailgun.client import (
    AsyncClient,
    Client,
    Config,
    RedactingFilter,
    SecureHTTPAdapter,
    SecurityGuard,
)
from mailgun.handlers.error_handler import ApiError
from mailgun.security import SecretAuth, SpamGuard


class TestSecurityGuardGeneral:
    """Core security validation logic for inputs and methods."""

    def test_sanitize_http_method_valid(self) -> None:
        assert SecurityGuard.sanitize_http_method("get") == "GET"
        assert SecurityGuard.sanitize_http_method(" PoSt  ") == "POST"

    def test_sanitize_http_method_invalid(self) -> None:
        with pytest.raises(ValueError, match="HTTP method 'TRACE' is prohibited"):
            SecurityGuard.sanitize_http_method("TRACE")

    def test_sanitize_domain_valid(self) -> None:
        assert SecurityGuard.sanitize_domain("test.com") == "test.com"
        assert SecurityGuard.sanitize_domain(None) is None

    def test_sanitize_domain_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="CRITICAL SECURITY: Path traversal"):
            SecurityGuard.sanitize_domain("../test.com")

    def test_sanitize_domain_advanced_traversal_and_crlf(self) -> None:
        crlf_domain = "mytest.com\r\nInject: Header"
        sanitized_crlf = SecurityGuard.sanitize_domain(crlf_domain)
        assert sanitized_crlf == "mytest.comInject: Header"

        slash_domain = "mytest.com/....//path"
        with pytest.raises(ValueError, match="Path traversal characters detected"):
            SecurityGuard.sanitize_domain(slash_domain)

    def test_validate_auth_strips_whitespace_and_rejects_newlines(self) -> None:
        clean_auth = SecurityGuard.validate_auth((" api ", " key "))
        assert clean_auth == ("api", "key")
        with pytest.raises(ValueError, match="Header Injection risk"):
            SecurityGuard.validate_auth(("api", "key\nwithnewline"))

    def test_secret_auth_hides_credentials(self) -> None:
        auth = SecretAuth(("api", "super-secret-key-123"))
        assert repr(auth) == "('api', '***REDACTED***')"
        assert auth[0] == "api"
        assert auth[1] == "super-secret-key-123"

    def test_sanitize_headers_valid(self) -> None:
        headers = {"Authorization": "Basic 123", "User-Agent": "test-agent"}
        assert SecurityGuard.sanitize_headers(headers) == headers

    def test_sanitize_headers_none(self) -> None:
        assert SecurityGuard.sanitize_headers(None) is None

    def test_sanitize_headers_crlf_injection(self) -> None:
        with pytest.raises(ValueError, match="CRLF injection detected"):
            SecurityGuard.sanitize_headers({"Evil-Header": "value\r\nInject: bad"})
        with pytest.raises(ValueError, match="CRLF injection detected"):
            SecurityGuard.sanitize_headers({"Evil-Header": "value\nInject: bad"})

    def test_secure_http_adapter_proxy_manager_for(self) -> None:
        adapter = SecureHTTPAdapter()
        proxy_manager = adapter.proxy_manager_for("http://proxy.local:8080")
        assert "ssl_context" in proxy_manager.connection_pool_kw
        assert proxy_manager.connection_pool_kw["ssl_context"].minimum_version.name == "TLSv1_2"

    def test_sanitize_timeout_httpx_obj_and_limit_exceeded(self) -> None:
        class DummyHttpxTimeout:
            connect = 5.0
            read = 15.0

        res = SecurityGuard.sanitize_timeout(DummyHttpxTimeout())
        assert res == (5.0, 15.0)

        with pytest.raises(ValueError, match="exceeds maximum allowed boundary"):
            SecurityGuard.sanitize_timeout(350.0)

    def test_validate_attachment_path_fallbacks(self, tmp_path: Any) -> None:
        test_file = tmp_path / "valid.txt"
        test_file.write_bytes(b"data")

        # Valid resolution without safe_base_dir
        res = SecurityGuard.validate_attachment_path(test_file, safe_base_dir=None)  # pyright: ignore[reportArgumentType]
        assert res == test_file.resolve()

        # Reject path traversal tokens
        # Use a string that passes the OS .exists() check but contains explicit ../ tokens
        traversal_path = str(test_file.parent) + "/../" + test_file.parent.name + "/valid.txt"
        with pytest.raises(ValueError, match="Path traversal tokens"):
            SecurityGuard.validate_attachment_path(traversal_path, safe_base_dir=None)  # pyright: ignore[reportArgumentType]

    def test_check_file_size_validations(self, tmp_path: Path) -> None:
        # Non-regular file (directory)
        with pytest.raises(ValueError, match="Path is not a regular file"):
            SecurityGuard.check_file_size(tmp_path)

        # File exceeding MB limit
        large_file = tmp_path / "large.bin"
        large_file.write_bytes(b"X" * (2 * 1024 * 1024))
        with pytest.raises(ValueError, match="File exceeds Mailgun's 1MB limit"):
            SecurityGuard.check_file_size(large_file, max_size_mb=1)

    def test_verify_webhook_crypto_math_and_expiration(self) -> None:
        signing_key = "secret_key"
        token = "token123"
        now = int(time.time())
        msg = f"{now}{token}".encode()
        sig = hmac.new(signing_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        # Valid webhook
        assert SecurityGuard.verify_webhook(signing_key, token, now, sig) is True

        # Expired webhook (TTL exceeded)
        expired_ts = now - 600
        assert SecurityGuard.verify_webhook(signing_key, token, expired_ts, sig) is False

    def test_normalize_domain_punycode(self) -> None:
        assert SecurityGuard.normalize_domain("укр.net") == "xn--j1amh.net"
        assert SecurityGuard.normalize_domain(None) == ""

    def test_check_file_size_directory(self, tmp_path: Path) -> None:
        """Coverage: Fails on non-regular files."""
        with pytest.raises(ValueError, match="not a regular file"):
            SecurityGuard.check_file_size(tmp_path)

    def test_verify_webhook_coverage(self) -> None:
        """Coverage: Hits type errors and expiration."""
        with pytest.raises(TypeError, match="must be a valid integer"):
            SecurityGuard.verify_webhook(b"key", "token", "invalid", "sig")
        assert SecurityGuard.verify_webhook(b"key", "token", 0, "sig") is False

    def test_normalize_domain_error(self) -> None:
        """Coverage: Hits UnicodeError fallback."""
        with pytest.raises(ValueError, match="Invalid domain name encoding"):
            # IDNA labels are strictly limited to 63 characters.
            # 64 characters deterministically triggers a UnicodeError.
            SecurityGuard.normalize_domain("a" * 64 + ".com")

    def test_validate_attachment_path_does_not_exist(self, tmp_path: Path) -> None:
        """Coverage: Files that do not exist."""
        with pytest.raises(ValueError, match="Invalid attachment path or not a file"):
            SecurityGuard.validate_attachment_path(tmp_path / "ghost.txt", safe_base_dir=tmp_path)

    def test_validate_attachment_path_forbidden_roots(self) -> None:
        """Coverage: Hardcoded forbidden roots fallback across OS environments."""
        with patch("mailgun.security.Path") as mock_path_cls:
            mock_target = MagicMock()
            mock_target.exists.return_value = True
            mock_target.is_file.return_value = True
            mock_target.parts = ("/", "etc", "sensitive_system_config.conf")
            mock_target.__str__.return_value = "/etc/sensitive_system_config.conf"  # type: ignore[attr-defined]
            mock_target.is_relative_to.return_value = False  # Prevent mock short-circuiting

            mock_path_cls.return_value.resolve.return_value = mock_target

            with pytest.raises(ValueError, match="Access to sensitive OS system directories"):
                SecurityGuard.validate_attachment_path("/etc/sensitive_system_config.conf", safe_base_dir=None)  # pyright: ignore[reportArgumentType]

    def test_verify_webhook_overflow_error(self) -> None:
        """Coverage: Massive timestamps triggering an OverflowError in the math blocks."""
        massive_ts = 10**310
        with pytest.raises(ValueError, match="Invalid cryptographic payload or timestamp out of bounds"):
            SecurityGuard.verify_webhook(b"key", "token", massive_ts, "sig")

    def test_analyze_html_image_with_alt_tag(self) -> None:
        """Coverage: Branches where the image is present and DOES have an alt tag."""
        report = SpamGuard.check_html("<html><body><img src='test.png' alt='logo'/></body></html>")
        assert report["score"] == 100.0
        assert report["is_safe"] is True

    def test_redacting_filter_deep_redact_types(self) -> None:
        """Coverage: Execute the deep redaction tree for all edge-case Python types."""
        from collections import namedtuple
        log_filter = RedactingFilter()
        LogData = namedtuple("LogData", ["key"])

        class CustomObj:
            def __init__(self) -> None:
                self.key = "key-secret"

        # Primitive Types
        assert log_filter._deep_redact(123) == 123
        assert log_filter._deep_redact(None) is None

        # NamedTuple
        nt = LogData(key="key-secret")
        res_nt = log_filter._deep_redact(nt)
        assert res_nt.key == "key-[REDACTED]"

        # Custom Class Object
        co = CustomObj()
        res_co = log_filter._deep_redact(co)
        assert res_co["key"] == "key-[REDACTED]"

        # Iterables
        assert log_filter._deep_redact(["key-123"]) == ["key-[REDACTED]"]
        assert log_filter._deep_redact({"key-123"}) == {"key-[REDACTED]"}

class TestSecurityGuardSSRFAndURL:
    """CWE-319, CWE-918, and URL validation logic."""

    def test_cleartext_http_is_blocked(self) -> None:
        with pytest.raises(ValueError, match="CWE-319"):
            SecurityGuard.sanitize_api_url("http://api.mailgun.net")

    def test_cleartext_http_allowed_for_localhost(self) -> None:
        assert SecurityGuard.sanitize_api_url("http://localhost:8080") == "http://localhost:8080"
        assert SecurityGuard.sanitize_api_url("http://127.0.0.1:9000") == "http://127.0.0.1:9000"

    def test_https_is_always_allowed(self) -> None:
        assert SecurityGuard.sanitize_api_url("https://api.mailgun.net") == "https://api.mailgun.net"

    def test_validate_mailgun_url_allowed(self) -> None:
        valid_urls = [
            "https://api.mailgun.net/v3/domains/test.com/messages/123",
            "http://localhost:8080/v3",
            "https://storage.mailgun.org/v3/messages/xyz",
            "http://127.0.0.1/test",
            "https://mailgun.com/api",
        ]
        for url in valid_urls:
            assert SecurityGuard.validate_mailgun_url(url) == url

    def test_validate_mailgun_url_blocked(self) -> None:
        invalid_urls = [
            "https://evil-hacker.com/steal",
            "https://mailgun.net.attacker.com/v3",
            "https://attacker-mailgun.net/v3",
            "https://mailgun.com.fake.net/config",
        ]
        for url in invalid_urls:
            with pytest.raises(ValueError, match="CWE-918"):
                SecurityGuard.validate_mailgun_url(url)

    def test_validate_mailgun_url_unparsable(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL format"):
            SecurityGuard.validate_mailgun_url("https://[::1")

    def test_validate_mailgun_url_missing_hostname(self) -> None:
        with pytest.raises(ValueError, match="Missing hostname"):
            SecurityGuard.validate_mailgun_url("http:///api/v3/messages")

    def test_validate_mailgun_url_forbidden_scheme(self) -> None:
        with pytest.raises(ValueError, match="CWE-319"):
            SecurityGuard.validate_mailgun_url("ftp://api.mailgun.net/v3")


class TestSecurityGuardPathSegments:
    """CWE-22, CWE-79, CWE-94, CWE-116 Path and Segment sanitization."""

    def test_client_webhook_path_traversal_prevention(self) -> None:
        client = Client(auth=("api", "key"))
        with patch("requests.Session.request") as mock_request:
            with pytest.raises(ValueError, match="CWE-22"):
                client.domains_webhooks.delete(domain="test.com", webhook_name="clicked/../../delete")
            mock_request.assert_not_called()

    def test_sanitize_path_segment_excessive_encoding(self) -> None:
        with pytest.raises(ValueError, match="CWE-116"):
            SecurityGuard.sanitize_path_segment("%25252E%25252E%25252F")

    def test_sanitize_path_segment_template_injection(self) -> None:
        with pytest.raises(ValueError, match="CWE-94"):
            SecurityGuard.sanitize_path_segment("{{config.secret_key}}")

    def test_sanitize_path_segment_xss(self) -> None:
        with pytest.raises(ValueError, match="CWE-79"):
            SecurityGuard.sanitize_path_segment("javascript:alert(1)")

    def test_sanitize_path_segment_none_and_invalid(self) -> None:
        assert SecurityGuard.sanitize_path_segment(None) == ""
        with pytest.raises(TypeError, match="Invalid segment type"):
            SecurityGuard.sanitize_path_segment({"invalid": "dict"})
        with pytest.raises(TypeError, match="Invalid segment type"):
            SecurityGuard.sanitize_path_segment(["list"])

    def test_sanitize_path_segment_without_sys(self) -> None:
        with patch.dict(sys.modules, {"sys": None}):
            with pytest.raises(ValueError, match="CWE-20"):
                SecurityGuard.sanitize_path_segment("bad\x00path")
            with pytest.raises(ValueError, match="CWE-22"):
                SecurityGuard.sanitize_path_segment("traversal/../path")


class TestSecurityGuardResourceExhaustion:
    """CWE-400 and file size limits."""

    def test_infinite_timeout_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Infinite timeouts are forbidden"):
            SecurityGuard.sanitize_timeout(None)

    def test_valid_timeout_passes_cleanly(self) -> None:
        assert SecurityGuard.sanitize_timeout((10.0, 60.0)) == (10.0, 60.0)
        assert SecurityGuard.sanitize_timeout(5.0) == 5.0

    @pytest.mark.parametrize("invalid_val", [
        float("inf"), float("nan"), 0, -1.5, (5.0,), (5.0, 10.0, 15.0),
        (float("nan"), 5.0), (5.0, float("inf")), (-2.0, 5.0),
    ])
    def test_sanitize_timeout_invalid_values(self, invalid_val: Any) -> None:
        with pytest.raises(ValueError, match="Timeout must be"):
            SecurityGuard.sanitize_timeout(invalid_val)

    @pytest.mark.parametrize("invalid_type", ["10.0", True, False, [5.0, 10.0], {"timeout": 5.0}])
    def test_sanitize_timeout_invalid_types(self, invalid_type: Any) -> None:
        with pytest.raises(TypeError, match="Timeout must be a numeric value"):
            SecurityGuard.sanitize_timeout(invalid_type)

    def test_check_file_size_safe(self, tmp_path: Any) -> None:
        dummy_file = tmp_path / "safe_file.txt"
        dummy_file.write_bytes(b"Safe content")
        SecurityGuard.check_file_size(dummy_file, max_size_mb=1)


class TestSecurityGuardUtilityAndFallbacks:
    """Misc coverage for logging and helper methods."""

    def test_sanitize_log_trace_fallback(self) -> None:
        assert SecurityGuard.sanitize_log_trace(None) == "None"
        assert SecurityGuard.sanitize_log_trace(12345) == "12345"
        assert SecurityGuard.sanitize_log_trace(["list", "item"]) == "['list', 'item']"

    def test_validate_no_control_characters_graceful_bypass(self) -> None:
        assert SecurityGuard.validate_no_control_characters(None) is None  # pyright: ignore[reportArgumentType]
        assert SecurityGuard.validate_no_control_characters("") is None
        assert SecurityGuard.validate_no_control_characters("123") is None


class TestLogSanitization:
    """Tests for RedactingFilter log safety (CWE-316, CWE-117)."""

    def test_redacting_filter_scrubs_secrets(self) -> None:
        log_filter = RedactingFilter()
        fake_private = "key-abcd1234efgh5678"
        fake_public = "pubkey-9876vutsqpon"
        fake_live = "key-live_112233"
        fake_zone = "pubkey-safe_zone"

        record_str = logging.LogRecord(
            name="mailgun.test", level=logging.INFO, pathname="client.py",
            lineno=10, msg=f"Sending message with api key: {fake_private}",
            args=(), exc_info=None
        )
        assert log_filter.filter(record_str) is True
        assert fake_private not in record_str.msg
        assert "key-[REDACTED]" in record_str.msg

        record_dict = logging.LogRecord(
            name="mailgun.test", level=logging.INFO, pathname="client.py",
            lineno=20, msg="Auth payload: %(secret)s",
            args=({"secret": fake_public},), exc_info=None
        )
        assert log_filter.filter(record_dict) is True
        if isinstance(record_dict.args, dict):
            assert record_dict.args["secret"] == "pubkey-[REDACTED]"  # pragma: allowlist secret

        record_tuple = logging.LogRecord(
            name="mailgun.test", level=logging.WARNING, pathname="client.py",
            lineno=30, msg="Failed to parse key: %s and %s",
            args=(fake_live, fake_zone), exc_info=None
        )
        assert log_filter.filter(record_tuple) is True
        if isinstance(record_tuple.args, tuple):
            assert record_tuple.args[0] == "key-[REDACTED]"
            assert record_tuple.args[1] == "pubkey-[REDACTED]"


class TestTransportSecurity:
    """Tests for TLS 1.2+ and System Audit hooks."""

    def test_secure_http_adapter_forces_tls12(self) -> None:
        with patch("requests.adapters.HTTPAdapter.init_poolmanager") as mock_super_init:
            adapter = SecureHTTPAdapter()
            adapter.init_poolmanager(connections=10, maxsize=10)
            kwargs = mock_super_init.call_args[1]
            ssl_ctx = kwargs["ssl_context"]
            assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_async_client_enforces_tls12_transport(self) -> None:
        client = AsyncClient(auth=("api", "key-mock"))
        ssl_ctx = client._client._transport._pool._ssl_context  # pyright: ignore[reportOptionalMemberAccess]
        assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    @patch("sys.audit")
    def test_sync_client_emits_audit_hook(self, mock_audit: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        client = Client(auth=("api", "key"))
        monkeypatch.setattr(client._session, "get", MagicMock(return_value=requests.Response()))
        client.domains.get()
        mock_audit.assert_called_with("mailgun.api.request", "GET", "https://api.mailgun.net/v3/domains")

    @pytest.mark.asyncio
    @patch("sys.audit")
    async def test_async_client_emits_audit_hook(self, mock_audit: MagicMock) -> None:
        """Verify that outbound requests from the async client trigger PEP 578 hooks."""
        client = AsyncClient(auth=("api", "key"))

        # Patch the transport directly
        with patch("httpx.AsyncHTTPTransport") as mock_transport_class:
            # Create a mock instance
            mock_transport_instance = AsyncMock()
            mock_transport_class.return_value = mock_transport_instance

            # Ensure handle_async_request is an AsyncMock that returns a valid response
            mock_transport_instance.handle_async_request = AsyncMock(
                return_value=compat_httpx.Response(200)
            )

            await client.domains.get()

            # Verify audit hook was called
            mock_audit.assert_called_with("mailgun.api.request", "GET", "https://api.mailgun.net/v3/domains")
            await client.aclose()


class TestExceptionSafety:
    """Tests for secure logging in error blocks."""

    @patch("mailgun.endpoints.logger.exception")
    def test_sync_timeout_exception_logs_safely(self, mock_logger_exc: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        client = Client(auth=("api", "key"))
        monkeypatch.setattr(client._session, "get", MagicMock(side_effect=requests.exceptions.Timeout("Read timed out")))
        with pytest.raises(TimeoutError):
            client.domains.get()
        assert "https://api.mailgun.net/v3/domains" in mock_logger_exc.call_args[0][2]

    @pytest.mark.asyncio
    @patch("mailgun.endpoints.logger.critical")
    async def test_async_connection_exception_logs_safely(self, mock_logger_crit: MagicMock) -> None:
        """Verify that when an async network failure occurs, the logger uses safe_url_for_log."""
        client = AsyncClient(auth=("api", "key"))

        with patch("mailgun.client.httpx.AsyncHTTPTransport") as mock_transport_class:
            mock_transport_instance = AsyncMock()
            mock_transport_class.return_value = mock_transport_instance

            # Set the side_effect on the async handler
            mock_transport_instance.handle_async_request = AsyncMock(
                side_effect=compat_httpx.ConnectError("DNS failure")
            )

            with pytest.raises(ApiError, match="Network routing failed"):
                await client.domains.get()

            # Verify the log captured the URL safely
            assert "https://api.mailgun.net/v3/domains" in mock_logger_crit.call_args[0][2]
            await client.aclose()


class TestArchitecture:
    """Performance and structural tests."""

    def test_config_url_baking_is_precomputed(self) -> None:
        config = Config(api_url="https://api.mailgun.net")
        assert config._baked_urls["v3"] == "https://api.mailgun.net/v3"
        assert config._build_base_url("v3") == "https://api.mailgun.net/v3/"

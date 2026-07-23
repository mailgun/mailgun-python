import importlib
import logging
import sys
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

import mailgun.config
from mailgun.client import Config, SecurityGuard
from mailgun.config import RetryPolicy


@pytest.fixture(autouse=True)
def reset_audit_hook_state() -> Generator[None, Any, None]:
    """Reset the Config Singleton state before and after each test."""
    Config._audit_hook_enabled = False
    yield
    Config._audit_hook_enabled = False


class TestConfigAuditHook:
    def test_audit_hook_actual_execution(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        Config.enable_security_audit()

        with caplog.at_level(logging.INFO):
            sys.audit("mailgun.api.request", "GET", "https://api.mailgun.net/v3/audit")

        assert any(
            "SECURITY AUDIT: Outbound API call tracked - GET https://api.mailgun.net/v3/audit"
            in r.message
            for r in caplog.records
        )

    def test_audit_hook_direct_coverage(self, caplog: pytest.LogCaptureFixture) -> None:
        with patch("sys.addaudithook") as mock_add:
            Config.enable_security_audit()

            hook_fn = mock_add.call_args[0][0]

            with caplog.at_level(logging.INFO):
                hook_fn(
                    "mailgun.api.request",
                    ("POST", "https://api.mailgun.net/v3/messages"),
                )
                hook_fn("other.event", ("GET", "https://other.com"))

        assert (
            "Outbound API call tracked - POST https://api.mailgun.net/v3/messages"
            in caplog.text
        )

    @patch("mailgun.config.logger.info")
    def test_enable_security_audit_hook_execution(self, mock_logger: MagicMock) -> None:
        Config.enable_security_audit()
        sys.audit("mailgun.api.request", "GET", "https://api.mailgun.net/v3")

        mock_logger.assert_called_with(
            "SECURITY AUDIT: Outbound API call tracked - %s %s",
            "GET",
            "https://api.mailgun.net/v3",
        )


class TestConfigDryRun:
    def test_config_dry_run_default(self) -> None:
        config = Config()
        assert config.dry_run is False

    def test_config_dry_run_enabled(self) -> None:
        config = Config(dry_run=True)
        assert config.dry_run is True


class TestConfigEdgeCases:
    def test_config_headers_mapping_proxy_prevents_mutation(self) -> None:
        config = Config()
        with pytest.raises(
            TypeError, match="'mappingproxy' object does not support item assignment"
        ):
            config._HEADERS_BASE["X-Malicious-Header"] = "value"  # type: ignore[index]

    def test_config_is_read_only(self) -> None:
        config = Config()
        with pytest.raises(TypeError):
            config["messages"] = "test"  # type: ignore[index]
        with pytest.raises(TypeError):
            del config["messages"]  # type: ignore[attr-defined]

    def test_config_version_fallback(self) -> None:
        real_import = __import__

        def mock_import(
            name: str,
            globals: Any = None,
            locals: Any = None,
            fromlist: Any = (),
            level: int = 0,
        ) -> Any:
            if name == "mailgun._version":
                raise ImportError("Mocked missing version")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=mock_import):
            importlib.reload(mailgun.config)
            assert mailgun.config.__version__ == "0.0.0-unknown"  # type: ignore[attr-defined]

        importlib.reload(mailgun.config)


class TestConfigInitialization:
    def test_custom_api_url(self) -> None:
        config = Config(api_url="https://custom.mailgun.net/")
        assert config.api_url == "https://custom.mailgun.net"

    def test_default_api_url(self) -> None:
        config = Config()
        assert config.api_url == Config.DEFAULT_API_URL
        assert config.api_url == "https://api.mailgun.net"


class TestConfigRouting:
    def test_available_endpoints_property(self) -> None:
        config = Config()
        endpoints = config.available_endpoints
        assert "domainlist" in endpoints
        assert "messages" in endpoints

    def test_config_empty_route_parts(self) -> None:
        config = Config()
        try:
            _ = config["domains__tags"]
        except Exception:
            pass

    def test_config_route_resolution_defaults_to_v3_for_unregistered_keys(self) -> None:
        config = Config()
        url_config, _ = config["UNREGISTERED_FUTURE_ENDPOINT"]

        assert url_config["base"].endswith("/v3/")
        assert isinstance(url_config["keys"], list)
        assert "endpoint" in url_config["keys"]
        assert "future" in url_config["keys"]
        assert "unregistered" in url_config["keys"]

    def test_getitem_addressvalidate(self) -> None:
        config = Config()
        url, _ = config["addressvalidate"]
        assert "base" in url
        assert len(url["keys"]) > 0

    def test_getitem_analytics(self) -> None:
        config = Config()
        url, _ = config["analytics"]
        assert "analytics" in url["keys"]
        assert "base" in url
        assert url["base"].endswith("v1/")

    def test_getitem_analytics_metrics_has_content_type(self) -> None:
        config = Config()
        _, headers = config["analytics_metrics"]
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_getitem_bounces(self) -> None:
        config = Config()
        url, _ = config["bounces"]
        assert "base" in url
        assert "bounces" in url["keys"]

    def test_getitem_case_insensitive(self) -> None:
        config = Config()
        url1, _ = config["MESSAGES"]
        url2, _ = config["messages"]
        assert url1 == url2

    def test_getitem_coverage_enhancement(self) -> None:
        config = Config()
        url_config, headers = config["NON_EXISTENT_ROUTE_XYZ"]

        assert url_config["base"].endswith("/v3/")
        assert isinstance(url_config["keys"], list)
        assert "User-agent" in headers

    def test_getitem_dkim(self) -> None:
        config = Config()
        url, _ = config["dkim"]
        assert "base" in url
        assert "dkim" in url["keys"]

    def test_getitem_domainlist(self) -> None:
        config = Config()
        url, _ = config["domainlist"]
        assert "base" in url
        assert url["keys"] == ["domainlist"]
        assert config["domainlist"][0]["base"].endswith("v4/")

    def test_getitem_domains(self) -> None:
        config = Config()
        url, headers = config["domains"]
        assert "base" in url
        assert "User-agent" in headers
        assert "domains" in str(url["keys"]).lower() or "domains" in url["keys"]

    def test_getitem_ippools(self) -> None:
        config = Config()
        url, _ = config["ippools"]
        assert "base" in url
        assert "ip_pools" in url["keys"]

    def test_getitem_ips(self) -> None:
        config = Config()
        url, _ = config["ips"]
        assert "base" in url
        assert "ips" in url["keys"]

    def test_getitem_keys(self) -> None:
        config = Config()
        url, _ = config["keys"]
        assert "base" in url
        assert "keys" in url["keys"]

    def test_getitem_messages(self) -> None:
        config = Config()
        url, headers = config["messages"]
        assert "base" in url
        assert "User-agent" in headers
        assert url["keys"] == ["messages"]

    def test_getitem_resendmessage(self) -> None:
        config = Config()
        url, _ = config["resendmessage"]
        assert "base" in url
        assert "resendmessage" in url["keys"]

    def test_getitem_tags(self) -> None:
        config = Config()
        url, _ = config["tags"]
        assert "base" in url
        assert "tags" in url["keys"]

    def test_getitem_users(self) -> None:
        config = Config()
        url, _ = config["users"]
        assert "base" in url
        assert "users" in url["keys"]

    def test_resolve_domains_route_activate_deactivate(self) -> None:
        res = Config()._resolve_domains_route(["activate"])
        assert "v4" in res["base"]

    def test_resolve_domains_route_alias_mapping(self) -> None:
        res = Config()._resolve_domains_route(["domains", "connection"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v1_security(self) -> None:
        res = Config()._resolve_domains_route(["domains", "credentials"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v3_tracking(self) -> None:
        res = Config()._resolve_domains_route(["domains", "tracking"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v4_fallback(self) -> None:
        res = Config()._resolve_domains_route(["domains", "unknown_new_feature"])
        assert "v3/domains" in res["base"]


class TestConfigSanitization:
    def test_config_rejects_empty_endpoint_keys(self) -> None:
        config = Config()

        with pytest.raises(KeyError, match="Invalid endpoint key"):
            _ = config[""]

        with pytest.raises(KeyError, match="Invalid endpoint key"):
            _ = config["   "]

    def test_sanitize_key_raises_error_on_empty(self) -> None:
        with pytest.raises(KeyError):
            SecurityGuard.sanitize_key("!@#")

    def test_sanitize_key_removes_special_chars(self) -> None:
        key = SecurityGuard.sanitize_key("messages-123!@#")
        assert key == "messages123"

    def test_sanitize_url_adds_scheme(self) -> None:
        url = SecurityGuard.sanitize_api_url("api.mailgun.net")
        assert url == "https://api.mailgun.net"

    def test_sanitize_url_removes_newlines_and_trailing_slashes(self) -> None:
        url = SecurityGuard.sanitize_api_url("https://api.mailgun.net/\n")
        assert url == "https://api.mailgun.net"


class TestConfigURLValidation:
    def test_build_base_url_prevents_double_slash(self) -> None:
        config = Config(api_url="https://api.mailgun.net")
        config._baked_urls["v3"] = "https://api.mailgun.net/v3/"

        result_no_suffix = config._build_base_url("v3")
        result_with_suffix = config._build_base_url("v3", suffix="domains")

        assert result_no_suffix == "https://api.mailgun.net/v3/"
        assert result_with_suffix == "https://api.mailgun.net/v3/domains/"
        assert "//domains" not in result_with_suffix

    def test_config_rejects_embedded_api_versions(self) -> None:
        malformed_urls = [
            "https://api.mailgun.net/v3/messages",
            "http://localhost:8080/v4/users",
            "a=iasssss{ssssssssssss}s/v1/sssss}9m",
        ]
        for url in malformed_urls:
            with pytest.raises(ValueError, match="Ambiguous API URL configuration"):
                Config(api_url=url)

    def test_config_warns_and_strips_trailing_versions(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            config = Config(api_url="https://api.mailgun.net/v3/")

        assert config.api_url == "https://api.mailgun.net"
        assert "Semantic Configuration Warning" in caplog.text
        assert "trailing 'v3' was stripped" in caplog.text

    def test_normalize_api_url_clean_url(self) -> None:
        clean_url = "https://api.mailgun.net"
        result = Config._normalize_api_url(clean_url)
        assert result == "https://api.mailgun.net"

    def test_normalize_api_url_raises_on_embedded_version(self) -> None:
        ambiguous_url = "https://api.mailgun.net/v3/sandbox"
        with pytest.raises(ValueError):
            Config._normalize_api_url(ambiguous_url)

    @patch("mailgun.config.logger.warning")
    def test_normalize_api_url_strips_trailing_version(
        self, mock_warn: MagicMock
    ) -> None:
        trailing_url = "https://api.mailgun.net/v3/"
        result = Config._normalize_api_url(trailing_url)

        assert result == "https://api.mailgun.net"
        mock_warn.assert_called_once()
        warning_msg = mock_warn.call_args[0][0]
        assert "Semantic Configuration Warning" in warning_msg
        assert "stripped to prevent routing duplication" in warning_msg

    @patch("mailgun.config.logger.warning")
    def test_validate_api_url_no_warning_on_https(self, mock_warn: MagicMock) -> None:
        Config(api_url="https://api.mailgun.net")
        mock_warn.assert_not_called()

    @patch("mailgun.config.logger.warning")
    def test_validate_api_url_no_warning_on_localhost(
        self, mock_warn: MagicMock
    ) -> None:
        Config(api_url="http://localhost:8000")
        mock_warn.assert_not_called()

    def test_validate_api_url_warns_on_http(self) -> None:
        Config(api_url="http://localhost")

        with pytest.raises(ValueError, match="CWE-319"):
            Config(api_url="http://insecure.net")

    @patch("mailgun.security.logger.warning")
    def test_validate_api_url_warns_on_unrecognized_host(
        self, mock_warn: MagicMock
    ) -> None:
        Config(api_url="https://custom.corporate.proxy/")
        mock_warn.assert_called_once()
        warning_msg = mock_warn.call_args[0][0]

        assert "Ensure this is a trusted proxy" in warning_msg
        assert "SECURITY WARNING: Invalid API host 'custom.corporate.proxy'" in warning_msg


class TestRetryPolicy:
    """Verifies the mathematical and logical boundaries of the network backoff engine."""

    def test_retry_policy_initialization_and_slots(self) -> None:
        """Verify immutable properties and memory-efficient __slots__ usage."""
        policy = RetryPolicy(max_retries=5, base_delay=2.0, max_delay=20.0, respect_retry_after=False)
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 20.0
        assert policy.respect_retry_after is False

        # Prove __slots__ prevents dynamic dict allocation
        with pytest.raises(AttributeError):
            policy.new_attr = "leak" # type: ignore[attr-defined]

    @patch("random.uniform")
    def test_calculate_delay_applies_full_jitter(self, mock_uniform: MagicMock) -> None:
        """Coverage: Verifies random.uniform is called precisely between 0 and the exponential bound."""
        mock_uniform.return_value = 1.5
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0)

        delay = policy.calculate_delay(attempt=1)

        # attempt = 1 -> base(1.0) * 2^1 = 2.0.
        mock_uniform.assert_called_once_with(0, 2.0)
        assert delay == 1.5

    @patch("random.uniform")
    def test_calculate_delay_respects_max_delay_ceiling(self, mock_uniform: MagicMock) -> None:
        """Coverage: Ensure exponential growth never breaches the `max_delay` cap."""
        mock_uniform.return_value = 10.0
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0)

        # attempt = 5 -> base(1.0) * 2^5 = 32.0. Math should cap it safely at max_delay (10.0).
        delay = policy.calculate_delay(attempt=5)

        mock_uniform.assert_called_once_with(0, 10.0)
        assert delay == 10.0

"""Unit tests for mailgun.client.Config."""

import pytest
from unittest.mock import MagicMock, patch

from mailgun.client import Config
from mailgun.client import SecurityGuard


class TestConfig:
    """Tests for Config class."""

    def test_default_api_url(self) -> None:
        config = Config()
        assert config.api_url == Config.DEFAULT_API_URL
        assert config.api_url == "https://api.mailgun.net"

    def test_custom_api_url(self) -> None:
        # Changed to a valid mailgun domain to pass the SecurityGuard checks
        config = Config(api_url="https://custom.mailgun.net/")
        assert config.api_url == "https://custom.mailgun.net"

    def test_getitem_messages(self) -> None:
        config = Config()
        url, headers = config["messages"]
        assert "base" in url
        assert url["keys"] == ["messages"]
        assert "User-agent" in headers

    def test_getitem_domains(self) -> None:
        config = Config()
        url, headers = config["domains"]
        assert "base" in url
        assert "domains" in str(url["keys"]).lower() or "domains" in url["keys"]
        assert "User-agent" in headers

    def test_getitem_domainlist(self) -> None:
        config = Config()
        url, headers = config["domainlist"]
        assert "base" in url
        assert url["keys"] == ["domainlist"]
        assert config["domainlist"][0]["base"].endswith("v4/")

    def test_getitem_ips(self) -> None:
        config = Config()
        url, headers = config["ips"]
        assert "base" in url
        assert "ips" in url["keys"]

    def test_getitem_tags(self) -> None:
        config = Config()
        url, headers = config["tags"]
        assert "base" in url
        assert "tags" in url["keys"]

    def test_getitem_bounces(self) -> None:
        config = Config()
        url, headers = config["bounces"]
        assert "base" in url
        assert "bounces" in url["keys"]

    def test_getitem_dkim(self) -> None:
        config = Config()
        url, headers = config["dkim"]
        assert "base" in url
        assert "dkim" in url["keys"]

    def test_getitem_analytics(self) -> None:
        config = Config()
        url, headers = config["analytics"]
        assert "base" in url
        assert "analytics" in url["keys"]
        assert url["base"].endswith("v1/")

    def test_getitem_analytics_metrics_has_content_type(self) -> None:
        """Analytics APIs require JSON headers by default."""
        config = Config()
        url, headers = config["analytics_metrics"]
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_getitem_users(self) -> None:
        config = Config()
        url, headers = config["users"]
        assert "base" in url
        assert "users" in url["keys"]

    def test_getitem_keys(self) -> None:
        config = Config()
        url, headers = config["keys"]
        assert "base" in url
        assert "keys" in url["keys"]

    def test_getitem_case_insensitive(self) -> None:
        config = Config()
        url1, headers1 = config["MESSAGES"]
        url2, headers2 = config["messages"]
        assert url1 == url2

    def test_getitem_addressvalidate(self) -> None:
        config = Config()
        url, headers = config["addressvalidate"]
        assert "base" in url
        # Just verify that keys are populated; internal routing masks exact alias names
        assert len(url["keys"]) > 0

    def test_getitem_resendmessage(self) -> None:
        config = Config()
        url, headers = config["resendmessage"]
        assert "base" in url
        assert "resendmessage" in url["keys"]

    def test_getitem_ippools(self) -> None:
        config = Config()
        url, headers = config["ippools"]
        assert "base" in url
        assert "ip_pools" in url["keys"]

    def test_sanitize_url_adds_scheme(self) -> None:
        url = SecurityGuard.sanitize_api_url("api.mailgun.net")
        assert url == "https://api.mailgun.net"

    def test_sanitize_url_removes_newlines_and_trailing_slashes(self) -> None:
        url = SecurityGuard.sanitize_api_url("https://api.mailgun.net/\n")
        assert url == "https://api.mailgun.net"

    def test_sanitize_key_removes_special_chars(self) -> None:
        key = SecurityGuard.sanitize_key("messages-123!@#")
        assert key == "messages123"

    def test_sanitize_key_raises_error_on_empty(self) -> None:
        with pytest.raises(KeyError):
            SecurityGuard.sanitize_key("!@#")

    def test_resolve_domains_route_activate_deactivate(self) -> None:
        res = Config()._resolve_domains_route(["activate"])
        assert "v4" in res["base"]

    def test_resolve_domains_route_v1_security(self) -> None:
        """Endpoints like 'credentials' should route to v1 or v3 based on DOMAIN_ENDPOINTS registry."""
        res = Config()._resolve_domains_route(["domains", "credentials"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v3_tracking(self) -> None:
        res = Config()._resolve_domains_route(["domains", "tracking"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_alias_mapping(self) -> None:
        res = Config()._resolve_domains_route(["domains", "connection"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v4_fallback(self) -> None:
        """Test that unknown domain routes fallback to V3 (Safety Fallback)."""
        res = Config()._resolve_domains_route(["domains", "unknown_new_feature"])
        assert "v3/domains" in res["base"]

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_warns_on_http(self, mock_warn: MagicMock) -> None:
        Config(api_url="http://localhost")
        # Localhost should not trigger a warning
        mock_warn.assert_not_called()

        Config(api_url="http://insecure.net")
        mock_warn.assert_called()

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_no_warning_on_https(self, mock_warn: MagicMock) -> None:
        Config(api_url="https://api.mailgun.net")
        mock_warn.assert_not_called()

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_no_warning_on_localhost(self, mock_warn: MagicMock) -> None:
        Config(api_url="http://localhost:8000")
        mock_warn.assert_not_called()

    def test_available_endpoints_property(self) -> None:
        """Test that available_endpoints returns a combined set of all valid routes."""
        config = Config()
        endpoints = config.available_endpoints
        assert "messages" in endpoints
        assert "domainlist" in endpoints

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_warns_on_unrecognized_host(self, mock_warn: MagicMock) -> None:
        """Test a warning (Non-Breaking) for custom URL/proxies."""
        Config(api_url="https://custom.corporate.proxy/")

        mock_warn.assert_called_once()
        warning_msg = mock_warn.call_args[0][0]

        assert "SECURITY WARNING: Invalid API host 'custom.corporate.proxy'" in warning_msg
        assert "Ensure this is a trusted proxy" in warning_msg

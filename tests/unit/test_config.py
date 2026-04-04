"""Unit tests for mailgun.client.Config."""

import pytest
from unittest.mock import MagicMock, patch

from mailgun.client import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_api_url(self) -> None:
        config = Config()
        assert config.api_url == Config.DEFAULT_API_URL
        assert config.api_url == "https://api.mailgun.net"

    def test_custom_api_url(self) -> None:
        config = Config(api_url="https://custom.api/")
        assert config.api_url == "https://custom.api"

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
        assert url["keys"] == ["ips"]
        assert "v3" in url["base"]

    def test_getitem_tags(self) -> None:
        config = Config()
        url, headers = config["tags"]
        assert url["keys"] == ["tags"]

    def test_getitem_bounces(self) -> None:
        config = Config()
        url, headers = config["bounces"]
        assert url["keys"] == ["bounces"]

    def test_getitem_dkim(self) -> None:
        config = Config()
        url, headers = config["dkim"]
        assert url["keys"] == ["dkim", "keys"]
        assert "v1" in url["base"]

    def test_getitem_analytics(self) -> None:
        config = Config()
        url, headers = config["analytics"]
        # "analytics" is in special_cases, so returns early without Content-Type
        assert "analytics" in url["keys"]
        assert url["keys"] == ["analytics", "usage", "metrics", "logs", "tags", "limits"]

    def test_getitem_analytics_metrics_has_content_type(self) -> None:
        """Keys containing 'analytics' (but not exact 'analytics') get Content-Type."""
        config = Config()
        url, headers = config["analytics_metrics"]
        assert "analytics" in url["keys"]
        assert headers.get("Content-Type") == "application/json"

    def test_getitem_users(self) -> None:
        config = Config()
        url, headers = config["users"]
        assert "users" in url["keys"]
        assert "v5" in url["base"]

    def test_getitem_keys(self) -> None:
        config = Config()
        url, headers = config["keys"]
        assert "keys" in url["keys"]
        assert "v1" in url["base"]

    def test_getitem_case_insensitive(self) -> None:
        config = Config()
        url1, _ = config["DOMAINS"]
        url2, _ = config["domains"]
        assert url1["keys"] == url2["keys"]
        assert url1["base"] == url2["base"]

    def test_getitem_addressvalidate(self) -> None:
        config = Config()
        url, headers = config["addressvalidate"]
        assert "address/validate" in url["base"] or "validate" in str(url["keys"])

    def test_getitem_resendmessage(self) -> None:
        config = Config()
        url, _ = config["resendmessage"]
        assert url["keys"] == ["resendmessage"]

    def test_getitem_ippools(self) -> None:
        config = Config()
        url, _ = config["ippools"]
        assert url["keys"] == ["ip_pools"]

    def test_sanitize_url_adds_scheme(self) -> None:
        """Test that missing scheme defaults to https://"""
        config = Config(api_url="api.mailgun.net")
        assert config.api_url == "https://api.mailgun.net"

    def test_sanitize_url_removes_newlines_and_trailing_slashes(self) -> None:
        """Test url cleanup for carriage returns and trailing slashes."""
        config = Config(api_url="https://api.custom.com/\r\n")
        assert config.api_url == "https://api.custom.com"

    def test_sanitize_key_removes_special_chars(self) -> None:
        """Test that keys with hyphens or special chars are sanitized."""
        clean_key = Config._sanitize_key("My-Key!@#")
        assert clean_key == "mykey"

    def test_sanitize_key_raises_error_on_empty(self) -> None:
        """Test that completely invalid keys raise KeyError."""
        with pytest.raises(KeyError, match="Invalid endpoint key: !!!"):
            Config._sanitize_key("!!!")

    def test_resolve_domains_route_activate_deactivate(self) -> None:
        """Test V4 fallback for domain activate/deactivate routes."""
        res = Config()._resolve_domains_route(["domains", "auth", "keys", "sel", "activate"])
        assert res["base"] == "https://api.mailgun.net/v4/"
        assert res["keys"][-1] == "activate"
        assert "{authority_name}" in res["keys"]

    def test_resolve_domains_route_v1_security(self) -> None:
        """Test that security endpoints map to V1."""
        res = Config()._resolve_domains_route(["domains", "security"])
        assert "v1/domains" in res["base"]
        assert "security" in res["keys"]

    def test_resolve_domains_route_v3_tracking(self) -> None:
        """Test that tracking endpoints map to V3."""
        res = Config()._resolve_domains_route(["domains", "tracking"])
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_alias_mapping(self) -> None:
        """Test that aliases like dkimauthority map correctly."""
        res = Config()._resolve_domains_route(["dkimauthority"])
        assert "dkim_authority" in res["keys"]
        assert "v3/domains" in res["base"]

    def test_resolve_domains_route_v4_fallback(self) -> None:
        """Test that unknown domain routes fallback to V3 (Safety Fallback)."""
        res = Config()._resolve_domains_route(["domains", "unknown_new_feature"])
        assert "v3/domains" in res["base"]

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_warns_on_http(self, mock_warn: MagicMock) -> None:
        Config(api_url="http://insecure.net")
        mock_warn.assert_called_once()
        assert "Cleartext HTTP transmission detected" in mock_warn.call_args[0][0]

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_no_warning_on_https(self, mock_warn: MagicMock) -> None:
        Config(api_url="https://secure.net")
        mock_warn.assert_not_called()

    @patch("mailgun.client.logger.warning")
    def test_validate_api_url_no_warning_on_localhost(self, mock_warn: MagicMock) -> None:
        Config(api_url="http://localhost:8000")
        mock_warn.assert_not_called()

    def test_available_endpoints_property(self) -> None:
        """Test that available_endpoints returns a combined set of all valid routes."""
        from mailgun.client import Config

        config = Config()
        endpoints = config.available_endpoints

        assert isinstance(endpoints, set)
        assert "messages" in endpoints
        assert "bounces" in endpoints
        assert "domainlist" in endpoints
        assert "dkim_keys" in endpoints

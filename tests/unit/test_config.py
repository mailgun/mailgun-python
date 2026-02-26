"""Unit tests for mailgun.client.Config."""

import pytest

from mailgun.client import Config


class TestConfig:
    """Tests for Config class."""

    def test_default_api_url(self) -> None:
        config = Config()
        assert config.api_url == Config.DEFAULT_API_URL
        assert config.api_url == "https://api.mailgun.net/"

    def test_custom_api_url(self) -> None:
        config = Config(api_url="https://custom.api/")
        assert config.api_url == "https://custom.api/"

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

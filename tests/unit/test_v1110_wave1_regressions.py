"""Wave 1 regression tests for mailgun v1.11.0 core transport, routing, and exports."""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

import mailgun
import mailgun.client
import mailgun.endpoints
from mailgun._httpx_compat import HAS_HTTPX2
from mailgun.client import AsyncClient, Client
from mailgun.config import Config
from mailgun.endpoints import AsyncEndpoint, BaseEndpoint
from mailgun.handlers import error_handler
from mailgun.handlers.error_handler import DeliverabilityError, MailgunTimeoutError
from mailgun.handlers.ip_pools_handler import handle_ippools
from mailgun.handlers.ips_handler import handle_ips


class TestOptionalHttpx2:
    def test_httpx_compat_exposes_flag(self) -> None:
        assert isinstance(HAS_HTTPX2, bool)

    def test_sync_client_works_without_httpx2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mailgun.client, "httpx2", None)
        monkeypatch.setattr(mailgun.endpoints, "httpx2", None)
        with Client(auth=("api", "key-test")) as client:
            ep = client.domains
            assert ep is not None

    def test_async_client_raises_clear_error_without_httpx2(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(mailgun.client, "httpx2", None)
        with pytest.raises(ImportError, match=r"mailgun\[async\]"):
            AsyncClient(auth=("api", "key-test"))

    def test_async_endpoint_raises_clear_error_without_httpx2(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(mailgun.endpoints, "httpx2", None)
        with pytest.raises(ImportError, match=r"mailgun\[async\]"):
            AsyncEndpoint(
                url={"base": "https://api.mailgun.net/v3/", "keys": ["domains"]},
                headers={},
                auth=("api", "key-test"),
            )

    def test_handle_api_error_without_httpx2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mailgun.endpoints, "httpx2", None)
        with pytest.raises(MailgunTimeoutError):
            BaseEndpoint._handle_api_error(
                requests.Timeout("timed out"),
                "GET",
                "https://api.mailgun.net/v3/domains",
            )


class TestExportsAndRouting:
    def test_deliverability_error_exported(self) -> None:
        assert mailgun.DeliverabilityError is DeliverabilityError
        assert "DeliverabilityError" in mailgun.__all__
        assert "DeliverabilityError" in error_handler.__all__

    @pytest.mark.parametrize(
        ("key", "expected_base", "expected_keys"),
        [
            ("preview_v2_tests", "https://api.mailgun.net/v2/", ["preview", "tests"]),
            (
                "reputationanalytics_v2_ips",
                "https://api.mailgun.net/v2/",
                ["reputationanalytics", "ips"],
            ),
            ("ip_pools_ips", "https://api.mailgun.net/v3/", ["ip_pools", "ips"]),
            ("dynamic_pools_ips", "https://api.mailgun.net/v3/", ["dynamic_pools", "ips"]),
            ("ip_warmups_ips", "https://api.mailgun.net/v3/", ["ip_warmups", "ips"]),
            ("ip_whitelist_ips", "https://api.mailgun.net/v2/", ["ip_whitelist", "ips"]),
            ("maverick_score_summary", "https://api.mailgun.net/v1/", ["maverick-score", "summary"]),
        ],
    )
    def test_multiword_prefix_routes_do_not_misroute(
        self,
        key: str,
        expected_base: str,
        expected_keys: list[str],
    ) -> None:
        config = Config()
        url, _ = config[key]
        assert url["base"] == expected_base
        assert url["keys"] == expected_keys

    def test_empty_double_underscore_domain_route_raises_keyerror(self) -> None:
        config = Config()
        with pytest.raises(KeyError, match="Invalid API endpoint requested"):
            _ = config["domains__tags"]

    def test_bounce_classification_exact_route_has_json_header(self) -> None:
        config = Config()
        _, headers = config["bounce_classification"]
        assert headers.get("Content-Type") == "application/json"

    @pytest.mark.parametrize(
        ("attr", "expected_url"),
        [
            ("address_bulk", "https://api.mailgun.net/v4/address/validate/bulk/my_list"),
            ("address_preview", "https://api.mailgun.net/v4/address/validate/preview/my_list"),
            ("addressvalidate", "https://api.mailgun.net/v4/address/validate/my_list"),
            ("address_validate_bulk", "https://api.mailgun.net/v4/address/validate/bulk/my_list"),
        ],
    )
    def test_address_routes_use_handle_address_validate(
        self,
        attr: str,
        expected_url: str,
    ) -> None:
        with Client(auth=("api", "key-test")) as client:
            ep = getattr(client, attr)
            assert BaseEndpoint.build_url(ep._url, list_name="my_list") == expected_url

    @patch("requests.Session.request")
    def test_addressparse_emits_deprecation_warning(self, mock_request: MagicMock) -> None:
        mock_request.return_value = MagicMock(status_code=200)
        with Client(auth=("api", "key-test")) as client, warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.addressparse.get()
        assert any(
            issubclass(item.category, DeprecationWarning) and "/v4/address/parse" in str(item.message)
            for item in w
        )

    def test_domains_x509_resolves_to_v2(self) -> None:
        res: dict[str, Any] = Config()._resolve_domains_route(["domains", "x509"])
        assert "v2/domains/" in res["base"]

    def test_handle_ippools_segment_order(self) -> None:
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["ip_pools", "ips"]}
        assert (
            handle_ippools(url, None, None, pool_id="pool1")
            == "https://api.mailgun.net/v3/ip_pools/pool1/ips"
        )
        assert (
            handle_ippools(url, None, None, pool_id="pool1", ip="1.1.1.1")
            == "https://api.mailgun.net/v3/ip_pools/pool1/ips/1.1.1.1"
        )

    def test_handle_ips_segment_order(self) -> None:
        url = {"base": "https://api.mailgun.net/v3/", "keys": ["ips", "domains"]}
        assert (
            handle_ips(url, None, None, ip="1.2.3.4")
            == "https://api.mailgun.net/v3/ips/1.2.3.4/domains"
        )

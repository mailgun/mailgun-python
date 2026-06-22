import re
import unittest
import warnings
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

from mailgun import routes
from mailgun.client import Client


class TestDeprecatedRegexes:
    def test_get_deprecated_regexes_is_cached(self) -> None:
        """Verify that the LRU cache prevents redundant regex compilations."""
        regexes1 = routes.get_deprecated_regexes()
        regexes2 = routes.get_deprecated_regexes()

        assert regexes1 is regexes2

    def test_get_deprecated_regexes_is_immutable(self) -> None:
        """Verify that the cached regex dictionary is immune to cache poisoning."""
        regexes = routes.get_deprecated_regexes()

        with pytest.raises(
            TypeError, match="'mappingproxy' object does not support item assignment"
        ):
            regexes[re.compile("new")] = "hacked"  # type: ignore[index]

        with pytest.raises(
            AttributeError, match="'mappingproxy' object has no attribute 'clear'"
        ):
            regexes.clear()  # type: ignore[attr-defined]

    def test_get_deprecated_regexes_returns_patterns(self) -> None:
        """Verify lazy compilation successfully parses strings into regex patterns."""
        regexes = routes.get_deprecated_regexes()

        assert isinstance(regexes, MappingProxyType)
        assert len(regexes) > 0
        for pattern, msg in regexes.items():
            assert isinstance(pattern, re.Pattern)
            assert isinstance(msg, str)


class TestRouteSchemas:
    def test_domain_aliases_schema(self) -> None:
        """Ensure DOMAIN_ALIASES is a flat mapping of strings."""
        assert isinstance(routes.DOMAIN_ALIASES, MappingProxyType)

        for alias, real_name in routes.DOMAIN_ALIASES.items():
            assert isinstance(alias, str)
            assert isinstance(real_name, str)
            assert alias.isalnum() or "_" in alias

    def test_domain_endpoints_schema(self) -> None:
        """Ensure DOMAIN_ENDPOINTS maps version strings to tuples of endpoint names."""
        assert isinstance(routes.DOMAIN_ENDPOINTS, MappingProxyType)

        assert "v1" in routes.DOMAIN_ENDPOINTS
        assert "v3" in routes.DOMAIN_ENDPOINTS

        for version, endpoints in routes.DOMAIN_ENDPOINTS.items():
            assert isinstance(version, str)
            assert version.startswith("v")
            assert isinstance(endpoints, tuple)
            assert endpoints
            assert all(isinstance(ep, str) for ep in endpoints)

    def test_exact_routes_schema(self) -> None:
        """Ensure EXACT_ROUTES matches MappingProxyType[str, tuple[str, tuple]]."""
        assert isinstance(routes.EXACT_ROUTES, MappingProxyType)
        assert routes.EXACT_ROUTES

        for key, value in routes.EXACT_ROUTES.items():
            assert isinstance(key, str)
            assert isinstance(value, tuple)
            assert len(value) == 2, f"Route '{key}' requires (version, keys_tuple)"

            version, keys_tuple = value
            assert isinstance(version, str)
            assert version.startswith("v"), f"Route '{key}' must start with 'v'"
            assert isinstance(keys_tuple, tuple)
            assert all(isinstance(k, str) for k in keys_tuple)

    def test_no_overlapping_keys(self) -> None:
        """Ensure overlaps between exact and prefix routes are strictly controlled."""
        exact_keys = set(routes.EXACT_ROUTES.keys())
        prefix_keys = set(routes.PREFIX_ROUTES.keys())

        intersection = exact_keys.intersection(prefix_keys)
        expected_overlaps = {"users"}

        assert intersection == expected_overlaps, (
            f"Unexpected overlaps found: {intersection - expected_overlaps}. "
            "If you added a new route, ensure it's either Exact or Prefix, "
            "but not both (unless intentionally used as a fallback)."
        )

    def test_prefix_routes_schema(self) -> None:
        """Ensure PREFIX_ROUTES matches MappingProxyType[str, tuple]."""
        assert isinstance(routes.PREFIX_ROUTES, MappingProxyType)
        assert routes.PREFIX_ROUTES

        for key, value in routes.PREFIX_ROUTES.items():
            assert isinstance(key, str)
            assert isinstance(value, tuple)
            assert len(value) == 3, f"Route '{key}' requires (version, suffix, key)"

            version, suffix, key_override = value
            assert isinstance(version, str)
            assert version.startswith("v"), f"Route '{key}' must start with 'v'"
            assert isinstance(suffix, str)
            assert key_override is None or isinstance(key_override, str)


class TestRoutingEngine(unittest.TestCase):
    """Dynamically test that the SDK supports every route in routes.py."""

    def setUp(self) -> None:
        """Initialize a dummy client for URL generation testing."""
        self.client = Client(auth=("api", "fake-api-key"))
        self.domain = "python.test.com"

    @patch("requests.Session.request")
    def test_all_endpoints_can_generate_urls(self, mock_request: MagicMock) -> None:
        """Verify that every mapped endpoint can generate a URL without KeyError."""
        mock_request.return_value = MagicMock(status_code=200)

        all_endpoints = set(routes.EXACT_ROUTES.keys()) | set(
            routes.PREFIX_ROUTES.keys()
        )

        failed_resolutions = []
        successful_urls = []

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            for endpoint_name in sorted(all_endpoints):
                if endpoint_name == "resend_message":
                    continue

                try:
                    ep = getattr(self.client, endpoint_name)
                    ep.get(domain=self.domain)

                    _method, target_url = (
                        mock_request.call_args[0]
                        if mock_request.call_args[0]
                        else (None, mock_request.call_args[1].get("url"))
                    )

                    if not target_url:
                        target_url = mock_request.call_args[1].get("url")

                    self.assertTrue(
                        str(target_url).startswith("https://api.mailgun.net/")
                    )
                    successful_urls.append(f"{endpoint_name} -> {target_url}")

                except Exception as e:
                    failed_resolutions.append(f"Route '{endpoint_name}' failed: {e}")

        self.assertEqual(
            len(failed_resolutions),
            0,
            f"URL generation failed for {len(failed_resolutions)} endpoints:\n"
            + "\n".join(failed_resolutions),
        )

        if successful_urls:
            print(
                f"\n[ROUTING ENGINE] Successfully validated {len(successful_urls)} routes."
            )

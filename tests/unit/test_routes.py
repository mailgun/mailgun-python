"""Unit tests for mailgun.routes configuration."""

from mailgun import routes


def test_exact_routes_schema() -> None:
    """Ensure EXACT_ROUTES matches the schema: dict[str, list[str, list[str]]]."""
    assert isinstance(routes.EXACT_ROUTES, dict)
    assert routes.EXACT_ROUTES

    for key, value in routes.EXACT_ROUTES.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert len(value) == 2, f"Route '{key}' must have exactly [version, keys_list]"

        version, keys_list = value
        assert isinstance(version, str)
        assert version.startswith("v"), f"Route '{key}' version '{version}' must start with 'v'"
        assert isinstance(keys_list, list)
        assert all(isinstance(k, str) for k in keys_list)


def test_prefix_routes_schema() -> None:
    """Ensure PREFIX_ROUTES matches the schema: dict[str, list[str, str, str | None]]."""
    assert isinstance(routes.PREFIX_ROUTES, dict)
    assert routes.PREFIX_ROUTES

    for key, value in routes.PREFIX_ROUTES.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert len(value) == 3, f"Route '{key}' must have exactly [version, suffix, key_override]"

        version, suffix, key_override = value
        assert isinstance(version, str)
        assert version.startswith("v"), f"Route '{key}' version '{version}' must start with 'v'"
        assert isinstance(suffix, str)
        assert key_override is None or isinstance(key_override, str)


def test_domain_aliases_schema() -> None:
    """Ensure DOMAIN_ALIASES is a flat mapping of strings."""
    assert isinstance(routes.DOMAIN_ALIASES, dict)

    for alias, real_name in routes.DOMAIN_ALIASES.items():
        assert isinstance(alias, str)
        assert isinstance(real_name, str)
        assert alias.isalnum() or "_" in alias


def test_domain_endpoints_schema() -> None:
    """Ensure DOMAIN_ENDPOINTS maps version strings to lists of endpoint names."""
    assert isinstance(routes.DOMAIN_ENDPOINTS, dict)

    # Must contain main versions
    assert "v1" in routes.DOMAIN_ENDPOINTS
    assert "v3" in routes.DOMAIN_ENDPOINTS

    for version, endpoints in routes.DOMAIN_ENDPOINTS.items():
        assert isinstance(version, str)
        assert version.startswith("v")
        assert isinstance(endpoints, list)
        assert endpoints
        assert all(isinstance(ep, str) for ep in endpoints)


def test_no_overlapping_keys() -> None:
    """Ensure overlaps between exact and prefix routes are strictly controlled.

    'analytics' and 'users' are allowed to overlap because they act as both
    exact endpoints (e.g. client.users) and prefixes for sub-routes
    (e.g. client.users_something).
    """
    exact_keys = set(routes.EXACT_ROUTES.keys())
    prefix_keys = set(routes.PREFIX_ROUTES.keys())

    intersection = exact_keys.intersection(prefix_keys)

    # Явно дозволяємо ці два ключі, оскільки це частина архітектури
    expected_overlaps = {"analytics", "users"}

    assert intersection == expected_overlaps, (
        f"Unexpected overlaps found: {intersection - expected_overlaps}. "
        "If you added a new route, ensure it's either Exact or Prefix, but not both "
        "(unless intentionally used as a fallback)."
    )

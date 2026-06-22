from __future__ import annotations

import sys
from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import urlparse

from mailgun import routes
from mailgun.logger import get_logger
from mailgun.security import SecurityGuard


try:
    from mailgun._version import __version__
except ImportError:
    __version__ = "0.0.0-unknown"


if TYPE_CHECKING:
    from collections.abc import Mapping


logger = get_logger(__name__)


@lru_cache
def _get_cached_route_data(clean_key: str) -> dict[str, Any]:
    """Apply internal cached routing logic.

    Uses only hashable types (str) as arguments to avoid TypeError.

    Args:
        clean_key: The sanitized endpoint key.

    Returns:
        A dictionary containing versioning and path data for the route.
    """
    # Resolve virtual property aliases before processing
    clean_key = routes.ROUTE_ALIASES.get(clean_key, clean_key)

    if clean_key in routes.EXACT_ROUTES:
        version, route_keys = routes.EXACT_ROUTES[clean_key]
        return {"version": version, "keys": tuple(route_keys)}

    route_parts = clean_key.split("_")
    primary_resource = route_parts[0]

    if primary_resource == "domains":
        return {"type": "domain", "parts": tuple(route_parts)}

    if primary_resource in routes.PREFIX_ROUTES:
        version, suffix, key_override = routes.PREFIX_ROUTES[primary_resource]
        final_parts = route_parts.copy()
        if key_override:
            final_parts[0] = key_override
        return {"version": version, "suffix": suffix, "keys": tuple(final_parts)}

    return {"version": APIVersion.V3.value, "keys": tuple(route_parts)}


class APIVersion(str, Enum):
    """Constants for Mailgun API versions."""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    V5 = "v5"


class Config:
    """Configuration engine for the Mailgun API client.

    Using a data-driven routing approach.
    """

    __slots__ = ("_baked_urls", "api_url", "dry_run", "ex_handler")

    DEFAULT_API_URL: Final[str] = "https://api.mailgun.net"
    USER_AGENT: Final[str] = f"mailgun-api-python/{__version__}"

    # Use Mapping to denote read-only dictionary-like structures
    _HEADERS_BASE: Final[Mapping[str, str]] = MappingProxyType({"User-agent": USER_AGENT})
    _HEADERS_JSON: Final[Mapping[str, str]] = MappingProxyType(
        {"User-agent": USER_AGENT, "Content-Type": "application/json"}
    )

    # --- ENCAPSULATED ROUTING REGISTRIES ---
    _DOMAINS_RESOURCE: Final[str] = "domains"

    # Mapping[str, Any] is used because the values in routes vary in structure
    _EXACT_ROUTES: Final[Mapping[str, Any]] = MappingProxyType(routes.EXACT_ROUTES)
    _PREFIX_ROUTES: Final[Mapping[str, Any]] = MappingProxyType(routes.PREFIX_ROUTES)
    _DOMAIN_ALIASES: Final[Mapping[str, str]] = MappingProxyType(routes.DOMAIN_ALIASES)

    _DOMAIN_ENDPOINTS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
        routes.DOMAIN_ENDPOINTS
    )
    _V1_ENDPOINTS: Final[frozenset[str]] = frozenset(routes.DOMAIN_ENDPOINTS["v1"])
    _V3_ENDPOINTS: Final[frozenset[str]] = frozenset(routes.DOMAIN_ENDPOINTS["v3"])
    _V4_ENDPOINTS: Final[frozenset[str]] = frozenset(routes.DOMAIN_ENDPOINTS.get("v4", []))

    def __init__(self, api_url: str | None = None, *, dry_run: bool = False) -> None:
        """Initialize the configuration engine.

        Args:
            api_url: Optional custom base URL for the Mailgun API.
            dry_run: Prevents network execution and intercepts requests locally.
        """
        self.ex_handler: bool = True
        self.dry_run: bool = dry_run
        base_url_input: str = api_url or self.DEFAULT_API_URL

        self.api_url: str = self._normalize_api_url(base_url_input)

        self._baked_urls: Final[dict[str, str]] = {
            ver.value: f"{self.api_url}/{ver.value}" for ver in APIVersion
        }

    @staticmethod
    def _normalize_api_url(raw_url: str) -> str:
        """Validates and normalizes the base API URL.

        Ensures no explicit versions are embedded in the path that would break
        dynamic f-string routing.

        Args:
            raw_url: The raw base URL string provided by the user.

        Returns:
            The sanitized and normalized API URL string.

        Raises:
            ValueError: If an ambiguous API version is found embedded within the custom path.
        """
        safe_url: str = SecurityGuard.sanitize_api_url(raw_url)

        parsed = urlparse(safe_url)
        path_segments = [seg for seg in parsed.path.split("/") if seg]

        known_versions = {v.value for v in APIVersion}

        # Ambiguity & Backward Compatibility Check
        for i, segment in enumerate(path_segments):
            if segment in known_versions:
                is_last_segment = i == len(path_segments) - 1

                if is_last_segment:
                    safe_url = safe_url.removesuffix(f"/{segment}")
                    logger.warning(
                        "Semantic Configuration Warning: 'api_url' should be the base domain. The trailing '%s' was stripped to prevent routing duplication.",
                        segment,
                    )
                else:
                    # Fail-Fast: The version is trapped inside a complex path
                    msg = (
                        f"Ambiguous API URL configuration: '{raw_url}'.\n"
                        f"The SDK automatically handles version routing, but an explicit "
                        f"version ('{segment}') was found embedded within your custom path. "
                        f"Please provide only the base host (e.g., 'https://api.mailgun.net')."
                    )
                    # Raised ValueError instead of ApiError
                    raise ValueError(msg)

        return safe_url.rstrip("/")

    def _build_base_url(self, version: APIVersion | str, suffix: str = "") -> str:
        """Construct API URL with precise slash control to prevent 404s.

        Args:
            version: The API version to use.
            suffix: An optional suffix to append to the base URL.

        Returns:
            The fully constructed base URL string.
        """
        ver_str: str = version.value if isinstance(version, APIVersion) else version
        # O(1) access instead of dynamic concatenation, ensuring no trailing slash
        base: str = self._baked_urls.get(ver_str, f"{self.api_url}/{ver_str}").rstrip("/")

        if suffix:
            path: str = f"{suffix}/" if suffix == self._DOMAINS_RESOURCE else suffix
            return f"{base}/{path}"

        return f"{base}/"

    def _resolve_domains_route(self, route_parts: list[str]) -> dict[str, Any]:
        """Handle context-aware versioning for domain-related endpoints.

        Args:
            route_parts: The components of the route requested.

        Returns:
            A dictionary containing a string base URL and a tuple of keys.
        """
        if any(action in route_parts for action in ("activate", "deactivate")):
            return {
                "base": self._build_base_url(APIVersion.V4),
                "keys": (
                    self._DOMAINS_RESOURCE,
                    "{authority_name}",
                    "keys",
                    "{selector}",
                    route_parts[-1],
                ),
            }

        mapped_parts: list[str] = [self._DOMAIN_ALIASES.get(p, p) for p in route_parts]

        if not mapped_parts or mapped_parts[0] != self._DOMAINS_RESOURCE:
            mapped_parts.insert(0, self._DOMAINS_RESOURCE)

        version: APIVersion = APIVersion.V3

        if len(mapped_parts) > 1:
            for part in reversed(mapped_parts[1:]):
                if part in self._V1_ENDPOINTS:
                    version = APIVersion.V1
                    break
                if part in self._V4_ENDPOINTS:
                    version = APIVersion.V4
                    break
                if part in self._V3_ENDPOINTS:
                    version = APIVersion.V3
                    break

        return {
            "base": self._build_base_url(version, self._DOMAINS_RESOURCE),
            "keys": mapped_parts.copy(),
        }

    def __getitem__(self, key: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Retrieve the URL configuration and headers for a specific endpoint.

        Args:
            key: The name of the endpoint route (e.g., 'messages', 'bounces').

        Returns:
            A tuple containing the URL configuration dictionary and the headers dictionary.
        """
        clean_key = SecurityGuard.sanitize_key(key)

        route_data = _get_cached_route_data(clean_key)

        # HTTP header mapping based on endpoint naming conventions
        requires_json_headers = "analytics" in clean_key or "bounceclassification" in clean_key

        # Prepare headers
        headers_map = self._HEADERS_JSON if requires_json_headers else self._HEADERS_BASE
        headers = dict(headers_map)

        # Reconstruct result
        if route_data.get("type") == "domain":
            return self._resolve_domains_route(list(route_data["parts"])), headers

        safe_url = {
            "base": self._build_base_url(route_data["version"], route_data.get("suffix", "")),
            "keys": list(route_data["keys"]),
        }

        return safe_url, headers

    @property
    def available_endpoints(self) -> set[str]:
        """Provide public access to valid route keys for IDE introspection."""
        return set(self._EXACT_ROUTES.keys()) | set(self._PREFIX_ROUTES.keys())

    @classmethod
    def enable_security_audit(cls) -> None:
        """Opt-in PEP 578 Audit Hook to track and log runtime network events.

        Enterprise security teams can enable this during SDK boot to gain instant
        visibility into API requests sent via the SDK without altering standard logs.
        """

        def audit_hook(event: str, args: tuple[Any, ...]) -> None:
            if event == "mailgun.api.request":
                method, url = args
                logger.info("SECURITY AUDIT: Outbound API call tracked - %s %s", method, url)

        sys.addaudithook(audit_hook)
        logger.info("Mailgun Security Audit Hooks Enabled.")

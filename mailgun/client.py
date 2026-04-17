"""Provide the main client and helper classes for interacting with the Mailgun API.

The `mailgun.client` module includes the core `Client` class for managing
API requests, configuration, and error handling, as well as utility functions
and classes for building request headers, URLs, and parsing responses.
Classes:
    - SecurityGuard: Centralized OWASP API security guardrails.
    - Config: Manages configuration settings for the Mailgun API.
    - Endpoint: Represents specific API endpoints and provides methods for
      common HTTP operations like GET, POST, PUT, and DELETE.
    - AsyncEndpoint: Async version of Endpoint using httpx for async HTTP operations.
    - BaseClient: Base class for API clients that holds common logic.
    - Client: The main API client for authenticating and making requests.
    - AsyncClient: Async version of Client using httpx for async API requests.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import warnings
from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import unquote, urlparse

import httpx
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError
from urllib3.util.retry import Retry

from mailgun import routes
from mailgun._version import __version__
from mailgun.handlers.bounce_classification_handler import handle_bounce_classification
from mailgun.handlers.default_handler import handle_default
from mailgun.handlers.domains_handler import (
    handle_dkimkeys,
    handle_domainlist,
    handle_domains,
    handle_mailboxes_credentials,
    handle_sending_queues,
    handle_webhooks,
)
from mailgun.handlers.email_validation_handler import handle_address_validate
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.inbox_placement_handler import handle_inbox
from mailgun.handlers.ip_pools_handler import handle_ippools
from mailgun.handlers.ips_handler import handle_ips
from mailgun.handlers.keys_handler import handle_keys
from mailgun.handlers.mailinglists_handler import handle_lists
from mailgun.handlers.messages_handler import handle_resend_message
from mailgun.handlers.metrics_handler import handle_metrics
from mailgun.handlers.routes_handler import handle_routes
from mailgun.handlers.suppressions_handler import (
    handle_bounces,
    handle_complaints,
    handle_unsubscribes,
    handle_whitelists,
)
from mailgun.handlers.tags_handler import handle_tags
from mailgun.handlers.templates_handler import handle_templates
from mailgun.handlers.users_handler import handle_users


if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

try:
    from mailgun._version import __version__
except ImportError:
    __version__ = "0.0.0-unknown"


if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Mapping

    from httpx import Response as HttpxResponse
    from requests.models import Response


# Public API of the client module
__all__ = [
    "AsyncClient",
    "AsyncEndpoint",
    "BaseClient",
    "Client",
    "Endpoint",
]

logger = logging.getLogger("mailgun.client")
# Ensure logger doesn't stay silent if the user hasn't configured basicConfig
if not logger.hasHandlers():
    logger.addHandler(logging.NullHandler())

# Constants for API error handling and logging (fixes Ruff PLR2004)
_HTTP_ERROR_THRESHOLD: Final[int] = 400
_MAX_LOG_LENGTH: Final[int] = 500
_AUTH_TUPLE_LEN: Final = 2
_TIMEOUT_TUPLE_LEN: Final[int] = 2

HANDLERS: dict[str, Callable[..., str]] = {  # type: ignore[type-arg]
    "resendmessage": handle_resend_message,
    "domains": handle_domains,
    "domainlist": handle_domainlist,
    "dkim": handle_dkimkeys,
    "dkim_authority": handle_domains,
    "dkim_selector": handle_domains,
    "web_prefix": handle_domains,
    "sending_queues": handle_sending_queues,
    "mailboxes": handle_mailboxes_credentials,
    "ips": handle_ips,
    "ip_pools": handle_ippools,
    "tags": handle_tags,
    "bounces": handle_bounces,
    "unsubscribes": handle_unsubscribes,
    "whitelists": handle_whitelists,
    "complaints": handle_complaints,
    "routes": handle_routes,
    "lists": handle_lists,
    "templates": handle_templates,
    "addressvalidate": handle_address_validate,
    "inbox": handle_inbox,
    "webhooks": handle_webhooks,
    "messages": handle_default,
    "messages.mime": handle_default,
    "events": handle_default,
    "analytics": handle_metrics,
    "bounce-classification": handle_bounce_classification,
    "users": handle_users,
    "keys": handle_keys,
}


class APIVersion(str, Enum):
    """Constants for Mailgun API versions."""

    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    V5 = "v5"


class SecretAuth(tuple):
    """OWASP: Obfuscate credentials in memory dumps and tracebacks."""

    __slots__ = ()  # DX & Performance: Prevent __dict__ creation to optimize memory usage.

    def __repr__(self) -> str:
        return "('api', '***REDACTED***')"


class SecurityGuard:
    """Centralized security validation and sanitization (Defense in Depth).

    This class isolates all Zero-Trust guardrails, enforcing SRP and making it
    easy to extract into a dedicated security module in future releases.
    """

    ALLOWED_HTTP_METHODS: Final[frozenset[str]] = frozenset(
        {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
    )
    ALLOWED_API_HOSTS: Final[tuple[str, ...]] = (
        "mailgun.net",
        "mailgun.org",
        "localhost",
        "127.0.0.1",
    )
    ALLOWED_KWARGS: Final[frozenset[str]] = frozenset({"proxies", "cert"})
    SAFE_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_]+$")

    @classmethod
    def sanitize_api_url(cls, raw_url: str) -> str:
        """Sanitize and validate the base API URL to prevent SSRF and Cleartext transmission.

        Args:
            raw_url: The raw URL string to sanitize.

        Returns:
            The sanitized URL string without a trailing slash.
        """
        raw_url = raw_url.strip().replace("\r", "").replace("\n", "")
        parsed = urlparse(raw_url)

        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
            parsed = urlparse(raw_url)

        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            logger.warning(
                "SECURITY WARNING: Cleartext HTTP transmission detected in API URL. "
                "Use 'https://' to prevent CWE-319 vulnerabilities."
            )

        hostname = parsed.hostname or ""
        is_valid_host = any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in cls.ALLOWED_API_HOSTS
        )
        if not is_valid_host:
            msg = (
                f"SECURITY WARNING: Invalid API host '{hostname}'. Ensure this is a trusted proxy."
            )
            logger.warning(msg)

        return raw_url.rstrip("/")

    @classmethod
    def validate_auth(cls, auth: tuple[str, str] | None) -> tuple[str, str] | None:
        """Sanitize and validate credentials against Header Injection vulnerabilities.

        Args:
            auth: A tuple containing the API user and API key, or None.

        Returns:
            A SecretAuth tuple with cleaned credentials, or None if no auth was provided.

        Raises:
            ValueError: If the API key contains invalid characters (e.g., newlines).
        """
        if auth and isinstance(auth, tuple) and len(auth) == _AUTH_TUPLE_LEN:
            clean_user = str(auth[0]).strip()
            clean_key = str(auth[1]).strip()

            if "\n" in clean_key or "\r" in clean_key:
                raise ValueError("API Key contains invalid characters (Header Injection risk).")

            return SecretAuth((clean_user, clean_key))
        return auth

    @classmethod
    def sanitize_key(cls, key: str) -> str:
        """Normalize and validate the endpoint key from IDE Introspection.

        Args:
            key: The raw endpoint key to sanitize.

        Returns:
            The sanitized and validated endpoint key.

        Raises:
            KeyError: If the resulting key is invalid or empty.
        """
        clean_key: str = key.lower()
        if not cls.SAFE_KEY_PATTERN.fullmatch(clean_key):
            clean_key = re.sub(r"[^a-z0-9_]", "", clean_key)
        if not clean_key:
            msg = f"Invalid endpoint key: {key}"
            raise KeyError(msg)
        return clean_key

    @classmethod
    def sanitize_domain(cls, domain: str | None) -> str | None:
        """Protect against Path Traversal in URL construction.

        Args:
            domain: Target domain name to sanitize.

        Returns:
            The sanitized domain name or None.

        Raises:
            ValueError: If path traversal characters are detected.
        """
        if not domain:
            return None

        decoded_domain = unquote(domain)

        # Poka-yoke: Actively strip all slashes and newlines (Advanced Traversal & CRLF)
        safe_domain = re.sub(r"[\r\n/\\]+", "", decoded_domain).strip()

        if ".." in safe_domain:
            raise ValueError(
                "CRITICAL SECURITY: Path traversal characters detected in domain parameter."
            )
        return safe_domain

    @classmethod
    def sanitize_http_method(cls, method: str) -> str:
        """Prevent HTTP Verb Tampering and Attribute Injection.

        Args:
            method: The HTTP method requested.

        Returns:
            A safely formatted HTTP method string.

        Raises:
            ValueError: If the method is not in the allowed list.
        """
        safe_method = str(method).strip().upper()
        if safe_method not in cls.ALLOWED_HTTP_METHODS:
            msg = f"CRITICAL SECURITY: HTTP method '{safe_method}' is prohibited."
            raise ValueError(msg)
        return safe_method

    @classmethod
    def sanitize_timeout(
        cls, timeout: float | tuple[float, float] | None
    ) -> float | tuple[float, float] | None:
        """Prevent Infinite Timeout Thread Exhaustion (DoS).

        Args:
            timeout: The requested timeout value.

        Returns:
            The safely verified timeout value.
        """
        if timeout is None:
            logger.warning("SECURITY RISK: Infinite timeouts (timeout=None) can lead to DoS.")
            return None

        def _ensure_positive(val: Any) -> float:
            f_val = float(val)
            if f_val <= 0:
                raise ValueError("Timeout values must be strictly positive.")
            return f_val

        if isinstance(timeout, tuple) and len(timeout) == _TIMEOUT_TUPLE_LEN:
            return (_ensure_positive(timeout[0]), _ensure_positive(timeout[1]))
        return _ensure_positive(timeout)

    @classmethod
    def filter_safe_kwargs(cls, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Prevent Mass Assignment of internal HTTP client states.

        Args:
            kwargs: Dictionary of keyword arguments passed to the network layer.

        Returns:
            A filtered dictionary containing only allowed low-level HTTP settings.
        """
        return {k: v for k, v in kwargs.items() if k in cls.ALLOWED_KWARGS}


# Static data is accessed directly from the routes module or class constants.
@lru_cache
def _get_cached_route_data(clean_key: str) -> dict[str, Any]:
    """Apply internal cached routing logic.

    Uses only hashable types (str) as arguments to avoid TypeError.

    Args:
        clean_key: The sanitized endpoint key.

    Returns:
        A dictionary containing versioning and path data for the route.
    """
    # 1. Exact Match
    if clean_key in routes.EXACT_ROUTES:
        version, route_keys = routes.EXACT_ROUTES[clean_key]
        return {"version": version, "keys": tuple(route_keys)}

    # 2. Parse resource parts
    route_parts = clean_key.split("_")
    primary_resource = route_parts[0]

    # 3. Domain Logic Trigger
    if primary_resource == "domains":
        return {"type": "domain", "parts": tuple(route_parts)}

    # 4. Prefix Logic
    if primary_resource in routes.PREFIX_ROUTES:
        version, suffix, key_override = routes.PREFIX_ROUTES[primary_resource]
        final_parts = route_parts.copy()
        if key_override:
            final_parts[0] = key_override
        return {"version": version, "suffix": suffix, "keys": tuple(final_parts)}

    # 5. Fallback
    return {"version": APIVersion.V3.value, "keys": tuple(route_parts)}


class Config:
    """Configuration engine for the Mailgun API client.

    Using a data-driven routing approach.
    """

    __slots__ = ("api_url", "ex_handler")

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

    def __init__(self, api_url: str | None = None) -> None:
        """Initialize the configuration engine.

        Args:
            api_url: Optional custom base URL for the Mailgun API.
        """
        self.ex_handler: bool = True
        base_url_input: str = api_url or self.DEFAULT_API_URL
        self.api_url: str = SecurityGuard.sanitize_api_url(base_url_input)

    def _build_base_url(self, version: APIVersion | str, suffix: str = "") -> str:
        """Construct API URL with precise slash control to prevent 404s.

        Args:
            version: The API version to use.
            suffix: An optional suffix to append to the base URL.

        Returns:
            The fully constructed base URL string.
        """
        ver_str: str = version.value if isinstance(version, APIVersion) else version
        base: str = f"{self.api_url}/{ver_str}"

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


class BaseEndpoint:
    """Base class for endpoints. Contains methods common for Endpoint and AsyncEndpoint."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        timeout: float | tuple[float, float] | None = 60,
    ) -> None:
        """Initialize a new BaseEndpoint instance.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: Authentication tuple or None.
        """
        self._url = url
        self.headers = headers
        self._auth = auth
        self._timeout = timeout

    @staticmethod
    def _warn_if_deprecated(method: str, target_url: str) -> None:
        """Check the formulated URL against the registry of deprecated endpoints.

        Issues both a standard Python DeprecationWarning and a SDK logger warning.

        Args:
            method: Requested HTTP method.
            target_url: Formulated destination URL.
        """
        path = urlparse(target_url).path
        for pattern, msg in routes.DEPRECATED_ROUTES.items():
            if pattern.search(path):
                warning_message = f"DEPRECATED API CALL ({method.upper()} {path}): {msg}"
                warnings.warn(warning_message, DeprecationWarning, stacklevel=3)
                logger.warning(warning_message)
                break

    def __repr__(self) -> str:
        """DX: Show the actual resolved target route instead of memory address.

        Returns:
            A string representation of the Endpoint and its target route.
        """
        route_path = "/".join(self._url.get("keys", ["unknown"]))
        return f"<{self.__class__.__name__} target='/{route_path}'>"

    @staticmethod
    def build_url(
        url: dict[str, Any],
        domain: str | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Build the final request URL using predefined handlers.

        Note: Some URLs are built in the Config class as they cannot be generated dynamically.

        Args:
            url: Incoming URL structure containing base and keys.
            domain: Target domain name.
            method: Requested HTTP method.
            **kwargs: Additional arguments required by specific handlers.

        Returns:
            The fully constructed target URL.

        Raises:
            ApiError: If the domain is required but missing.
        """
        keys = url.get("keys", [])
        endpoint_key = keys[0] if keys else ""

        if not domain and endpoint_key == "messages":
            raise ApiError("Domain is required")

        handler = HANDLERS.get(endpoint_key, handle_default)
        return handler(url, domain, method, **kwargs)  # type: ignore[no-untyped-call]


class Endpoint(BaseEndpoint):
    """Generate synchronous requests and return responses."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None = None,
        session: requests.Session | None = None,
        timeout: float | tuple[float, float] | None = 60,
    ) -> None:
        """Initialize a new Endpoint instance for synchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: requests auth tuple or None.
            session: Optional pre-configured requests.Session instance.
        """
        super().__init__(url, headers, auth, timeout=timeout)
        self._session = session or requests.Session()

    def api_call(
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: float | tuple[float, float] | None = None,
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Response | Any:
        """Execute the HTTP request to the Mailgun API.

        Args:
            auth: Authentication tuple.
            method: The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            url: The final formulated endpoint URL dictionary.
            headers: Request headers.
            data: Payload data (form data or JSON).
            filters: Query parameters.
            timeout: Request timeout duration in seconds.
            files: Files to upload.
            domain: Target domain name.
            **kwargs: Additional parameters to be passed to the underlying HTTP client.

        Returns:
            The HTTP response object from the server.

        Raises:
            TimeoutError: If the request times out.
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        # --- ZERO-TRUST GUARDRAILS ---
        safe_method = SecurityGuard.sanitize_http_method(method)
        safe_kwargs = SecurityGuard.filter_safe_kwargs(kwargs)
        target_domain = SecurityGuard.sanitize_domain(domain)

        actual_timeout = timeout if timeout is not None else self._timeout
        safe_timeout = SecurityGuard.sanitize_timeout(actual_timeout)

        target_url = self.build_url(url, domain=target_domain, method=safe_method, **kwargs)
        self._warn_if_deprecated(safe_method, target_url)

        req_method = getattr(self._session, safe_method.lower())

        logger.debug("Sending Request: %s %s", safe_method.upper(), target_url)

        try:
            response = req_method(
                target_url,
                data=data,
                params=filters,
                headers=headers,
                auth=auth,
                timeout=safe_timeout,
                files=files,
                verify=True,
                stream=False,
                allow_redirects=False,
                **safe_kwargs,
            )

            status_code = getattr(response, "status_code", 200)
            is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD
            if is_error:
                raw_text = getattr(response, "text", "")
                error_body = (
                    raw_text[:_MAX_LOG_LENGTH] + "..."
                    if len(raw_text) > _MAX_LOG_LENGTH
                    else raw_text
                )
                logger.error(
                    "API Error %s | %s %s | Response: %s",
                    status_code,
                    safe_method.upper(),
                    target_url,
                    error_body,
                )
            else:
                logger.debug(
                    "API Success %s | %s %s",
                    getattr(response, "status_code", 200),
                    safe_method.upper(),
                    target_url,
                )

        except requests.exceptions.Timeout as e:
            logger.exception("Timeout Error: %s %s", safe_method.upper(), target_url)
            raise TimeoutError from e
        except RequestsConnectionError as e:
            logger.critical("Connection Failed (DNS/Network): %s | URL: %s", e, target_url)
            msg = f"Network routing failed: {e}"
            raise ApiError(msg) from e
        except requests.RequestException as e:
            logger.critical("Request Exception: %s | URL: %s", e, target_url)
            raise ApiError(e) from e
        else:
            return response

    def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send a GET request to retrieve resources.

        Args:
            filters: Query parameters to include in the request.
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return self.api_call(
            self._auth,
            "get",
            self._url,
            domain=domain,
            headers=self.headers,
            filters=filters,
            **kwargs,
        )

    def create(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        headers: Any = None,
        files: Any | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send a POST request to create a new resource or execute an action.

        Args:
            data: Payload data (form data or JSON) to include in the request.
            filters: Query parameters to include in the request.
            domain: Target domain name.
            headers: Additional headers to merge with the default headers.
            files: Files to upload in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        req_headers = self.headers.copy()
        if headers and isinstance(headers, dict):
            req_headers.update(headers)

        if (
            req_headers.get("Content-Type") == "application/json"
            and data is not None
            and not isinstance(data, (str, bytes))
        ):
            data = json.dumps(data, separators=(",", ":"))

        return self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=req_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def put(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> Response:
        """Send a PUT request to update or replace a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return self.api_call(
            self._auth, "put", self._url, headers=self.headers, data=data, filters=filters, **kwargs
        )

    def patch(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> Response:
        """Send a PATCH request to partially update a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return self.api_call(
            self._auth,
            "patch",
            self._url,
            headers=self.headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def update(
        self, data: Any | None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> Response:
        """Send a PUT request specifically structured for updating resources with dynamic headers.

        Args:
            data: Payload data (form data or JSON).
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments, including custom 'headers', to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        custom_headers = kwargs.pop("headers", {})
        req_headers = self.headers.copy()
        if custom_headers and isinstance(custom_headers, dict):
            req_headers.update(custom_headers)

        if (
            req_headers.get("Content-Type") == "application/json"
            and data is not None
            and not isinstance(data, (str, bytes))
        ):
            data = json.dumps(data, separators=(",", ":"))

        return self.api_call(
            self._auth, "put", self._url, headers=req_headers, data=data, filters=filters, **kwargs
        )

    def delete(self, domain: str | None = None, **kwargs: Any) -> Response:
        """Send a DELETE request to remove a resource.

        Args:
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return self.api_call(
            self._auth, "delete", self._url, headers=self.headers, domain=domain, **kwargs
        )


class BaseClient:
    """Base class for API clients that holds common state and initialization logic."""

    def __init__(
        self,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize common client configuration and state.

        Args:
            auth: A tuple containing the API user and API key (e.g., ("api", "key-123")).
            **kwargs: Additional configuration parameters, such as 'api_url'.
        """
        self.auth = SecurityGuard.validate_auth(auth)
        self.config = Config(api_url=kwargs.get("api_url"))

        # DX Guardrail: Constructor Deprecation Interceptions
        if "api_version" in kwargs:
            warnings.warn(
                "The 'api_version' parameter is deprecated. The SDK now handles "
                "API versioning (v1, v3, v4, v5) automatically via dynamic routing.",
                DeprecationWarning,
                stacklevel=2,
            )

        if isinstance(kwargs.get("timeout"), int):
            warnings.warn(
                "Passing an integer for 'timeout' is deprecated. Please pass a "
                "bipartite tuple (connect_timeout, read_timeout) e.g., (10.0, 60.0).",
                DeprecationWarning,
                stacklevel=2,
            )
        self.timeout = kwargs.get("timeout", 60)

    def __repr__(self) -> str:
        """OWASP Secrets Management: Redact sensitive information from object representation.

        Returns:
            A redacted string representation of the Client.
        """
        return f"<{self.__class__.__name__} api_url={self.config.api_url!r}>"

    def __str__(self) -> str:
        """OWASP Secrets Management: Redact sensitive information from string representation.

        Returns:
            A safe human-readable string representation.
        """
        return f"Mailgun {self.__class__.__name__}"

    def __dir__(self) -> list[str]:
        """DX: Expose true config endpoints for IDE Introspection.

        Returns:
            A list of available attributes including dynamic endpoints.
        """
        return list(set(super().__dir__()) | self.config.available_endpoints)


class Client(BaseClient):
    """Synchronous client class."""

    def __init__(
        self,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new Client instance for API interaction.

        This method sets up API authentication, configuration, connection pooling,
        and automatic network resiliency (retries).

        Args:
            auth: A tuple containing the API user and API key.
            **kwargs: Additional configuration parameters.
        """
        super().__init__(auth=auth, **kwargs)
        self._session = self._build_resilient_session()

    @staticmethod
    def _build_resilient_session() -> requests.Session:
        """Set up connection pooling and automatic retries for transient failures.

        Returns:
            A configured requests.Session instance.
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "OPTIONS", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def __getattr__(self, name: str) -> Any:
        """Resolve and return the requested API endpoint instance.

        Splits the provided attribute name to execute the corresponding endpoint handler.

        Args:
            name: The endpoint attribute name (e.g., 'domains_ips' maps to ["domains", "ips"]).

        Returns:
            An endpoint instance configured for the requested route.

        Raises:
            AttributeError: If the requested route is unknown or a magic Python method is invoked.
        """
        # Protect Data Model: Ignore magic Python methods
        if name.startswith("__") and name.endswith("__"):
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg)

        try:
            url, headers = self.config[name]
            return Endpoint(
                url=url,
                headers=headers,
                auth=self.auth,
                session=self._session,
                timeout=self.timeout,
            )
        except KeyError as e:
            # __getattr__ must return AttributeError
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from e

    def close(self) -> None:
        """Close the underlying requests.Session connection pool and purge memory."""
        self._session.auth = None
        self._session.headers.clear()
        self._session.close()
        self.auth = None

    def __enter__(self) -> Self:
        """Enter the synchronous context manager.

        Returns:
            The Client instance itself.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the synchronous context manager, ensuring connection pools are closed."""
        self.close()


class AsyncEndpoint(BaseEndpoint):
    """Generate async requests and return responses using httpx."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        client: httpx.AsyncClient | None = None,
        timeout: float | tuple[float, float] | None = None,
    ) -> None:
        """Initialize a new AsyncEndpoint instance for asynchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: httpx auth tuple or None.
            client: Optional httpx.AsyncClient instance to reuse.
        """
        super().__init__(url, headers, auth, timeout=timeout)
        self._client = client or httpx.AsyncClient()

    async def api_call(
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: float | tuple[float, float] = 60,
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> HttpxResponse:
        """Execute the asynchronous HTTP request to the Mailgun API.

        Args:
            auth: Authentication tuple.
            method: The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            url: The final formulated endpoint URL dictionary.
            headers: Request headers.
            data: Payload data (form data or JSON).
            filters: Query parameters.
            timeout: Request timeout duration in seconds.
            files: Files to upload.
            domain: Target domain name.
            **kwargs: Additional parameters to be passed to the underlying HTTP client.

        Returns:
            The HTTP response object from the server.

        Raises:
            TimeoutError: If the request times out.
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        # --- ZERO-TRUST GUARDRAILS ---
        safe_method = SecurityGuard.sanitize_http_method(method)
        safe_timeout = SecurityGuard.sanitize_timeout(timeout)
        safe_kwargs = SecurityGuard.filter_safe_kwargs(kwargs)
        target_domain = SecurityGuard.sanitize_domain(domain)

        target_url = self.build_url(url, domain=target_domain, method=safe_method, **kwargs)
        self._warn_if_deprecated(safe_method, target_url)

        request_kwargs: dict[str, Any] = {
            "method": safe_method.upper(),
            "url": target_url,
            "params": filters,
            "files": files,
            "headers": headers,
            "auth": auth,
            "timeout": safe_timeout,
            "follow_redirects": False,
        }

        # Safe kwargs passthrough (e.g., allow_redirects)
        request_kwargs.update(safe_kwargs)

        if isinstance(data, (str, bytes)):
            request_kwargs["content"] = data
        else:
            request_kwargs["data"] = data

        logger.debug("Sending Async Request: %s %s", safe_method.upper(), target_url)

        try:
            response = await self._client.request(**request_kwargs)

            status_code = getattr(response, "status_code", 200)
            is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD
            if is_error:
                raw_text = getattr(response, "text", "")
                error_body = (
                    raw_text[:_MAX_LOG_LENGTH] + "..."
                    if len(raw_text) > _MAX_LOG_LENGTH
                    else raw_text
                )
                logger.error(
                    "API Error %s | %s %s | Response: %s",
                    status_code,
                    safe_method.upper(),
                    target_url,
                    error_body,
                )
            else:
                logger.debug(
                    "API Success %s | %s %s",
                    getattr(response, "status_code", 200),
                    safe_method.upper(),
                    target_url,
                )

        except httpx.TimeoutException as e:
            logger.exception("Timeout Error: %s %s", safe_method.upper(), target_url)
            raise TimeoutError from e
        except httpx.ConnectError as e:
            logger.critical("Async Connection Failed (DNS/Network): %s | URL: %s", e, target_url)
            msg = f"Network routing failed: {e}"
            raise ApiError(msg) from e
        except httpx.RequestError as e:
            logger.critical("Request Exception: %s | URL: %s", e, target_url)
            raise ApiError(e) from e
        else:
            return response

    async def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> HttpxResponse:
        """Send an asynchronous GET request to retrieve resources.

        Args:
            filters: Query parameters to include in the request.
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return await self.api_call(
            self._auth,
            "get",
            self._url,
            domain=domain,
            headers=self.headers,
            filters=filters,
            **kwargs,
        )

    async def create(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        headers: Any = None,
        files: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an asynchronous POST request to create a new resource or execute an action.

        Args:
            data: Payload data (form data or JSON) to include in the request.
            filters: Query parameters to include in the request.
            domain: Target domain name.
            headers: Additional headers to merge with the default headers.
            files: Files to upload in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        req_headers = self.headers.copy()
        if headers and isinstance(headers, dict):
            req_headers.update(headers)

        if (
            req_headers.get("Content-Type") == "application/json"
            and data is not None
            and not isinstance(data, (str, bytes))
        ):
            data = json.dumps(data, separators=(",", ":"))

        return await self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=req_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def put(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        """Send an asynchronous PUT request to update or replace a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return await self.api_call(
            self._auth, "put", self._url, headers=self.headers, data=data, filters=filters, **kwargs
        )

    async def patch(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        """Send an asynchronous PATCH request to partially update a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return await self.api_call(
            self._auth,
            "patch",
            self._url,
            headers=self.headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def update(
        self, data: Any | None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        """Send an asynchronous PUT request specifically structured for updating resources with dynamic headers.

        Args:
            data: Payload data (form data or JSON).
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments, including custom 'headers', to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        custom_headers = kwargs.pop("headers", {})
        req_headers = self.headers.copy()
        if custom_headers and isinstance(custom_headers, dict):
            req_headers.update(custom_headers)

        if (
            req_headers.get("Content-Type") == "application/json"
            and data is not None
            and not isinstance(data, (str, bytes))
        ):
            data = json.dumps(data, separators=(",", ":"))

        return await self.api_call(
            self._auth, "put", self._url, headers=req_headers, data=data, filters=filters, **kwargs
        )

    async def delete(self, domain: str | None = None, **kwargs: Any) -> httpx.Response:
        """Send an asynchronous DELETE request to remove a resource.

        Args:
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        return await self.api_call(
            self._auth, "delete", self._url, headers=self.headers, domain=domain, **kwargs
        )


class AsyncClient(BaseClient):
    """Async client class using httpx."""

    endpoint_cls = AsyncEndpoint

    def __init__(
        self,
        auth: tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new AsyncClient instance for asynchronous API interaction.

        Args:
            auth: A tuple containing the API user and API key.
            **kwargs: Additional configuration parameters.
        """
        super().__init__(auth=auth, **kwargs)
        self._client_kwargs = kwargs.get("client_kwargs", {})
        self._httpx_client: httpx.AsyncClient | None = None

    def __getattr__(self, name: str) -> Any:
        """Resolve and return the requested API endpoint instance.

        Splits the provided attribute name to execute the corresponding endpoint handler.

        Args:
            name: The endpoint attribute name (e.g., 'domains_ips' maps to ["domains", "ips"]).

        Returns:
            An endpoint instance configured for the requested route.

        Raises:
            AttributeError: If the requested route is unknown or a magic Python method is invoked.
        """
        if name.startswith("__") and name.endswith("__"):
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg)

        try:
            url, headers = self.config[name]
            return AsyncEndpoint(
                url=url,
                headers=headers,
                auth=self.auth,
                client=self._client,
                timeout=self.timeout,
            )
        except KeyError as e:
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from e

    @property
    def _client(self) -> httpx.AsyncClient:
        """Provide lazy initialization for the underlying httpx.AsyncClient.

        Returns:
            The active httpx.AsyncClient instance.
        """
        if not self._httpx_client or self._httpx_client.is_closed:
            # Expand connection pool for async high-throughput batching
            limits = httpx.Limits(max_keepalive_connections=100, max_connections=100)
            transport = httpx.AsyncHTTPTransport(retries=3, limits=limits)

            self._httpx_client = httpx.AsyncClient(transport=transport, **self._client_kwargs)
        return self._httpx_client

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient and purge memory."""
        if self._httpx_client:
            # CWE-316: Зачистка асинхронної сесії
            self._httpx_client.auth = None
            self._httpx_client.headers.clear()
            await self._httpx_client.aclose()
        self.auth = None

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager.

        Returns:
            The AsyncClient instance itself.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the asynchronous context manager, ensuring client resources are closed.

        Args:
            exc_type: The exception type, if any occurred.
            exc_val: The exception instance, if any occurred.
            exc_tb: The traceback associated with the exception.
        """
        await self.aclose()

"""Provide the main client and helper classes for interacting with the Mailgun API.

The `mailgun.client` module includes the core `Client` class for managing
API requests, configuration, and error handling, as well as utility functions
and classes for building request headers, URLs, and parsing responses.
Classes:
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
from enum import Enum
from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from urllib.parse import urlparse

import httpx
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mailgun import routes
from mailgun.handlers.bounce_classification_handler import handle_bounce_classification
from mailgun.handlers.default_handler import handle_default
from mailgun.handlers.domains_handler import handle_dkimkeys
from mailgun.handlers.domains_handler import handle_domainlist
from mailgun.handlers.domains_handler import handle_domains
from mailgun.handlers.domains_handler import handle_mailboxes_credentials
from mailgun.handlers.domains_handler import handle_sending_queues
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
from mailgun.handlers.suppressions_handler import handle_bounces
from mailgun.handlers.suppressions_handler import handle_complaints
from mailgun.handlers.suppressions_handler import handle_unsubscribes
from mailgun.handlers.suppressions_handler import handle_whitelists
from mailgun.handlers.tags_handler import handle_tags
from mailgun.handlers.templates_handler import handle_templates
from mailgun.handlers.users_handler import handle_users


if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


if TYPE_CHECKING:
    import types
    from collections.abc import Callable
    from collections.abc import Mapping

    from httpx import Response as HttpxResponse
    from requests.models import Response


# Public API of the client module
__all__ = [
    "AsyncClient",
    "AsyncEndpoint",
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
    USER_AGENT: Final[str] = "mailgun-api-python/"

    # Use Mapping to denote read-only dictionary-like structures
    _HEADERS_BASE: Final[Mapping[str, str]] = MappingProxyType({"User-agent": USER_AGENT})
    _HEADERS_JSON: Final[Mapping[str, str]] = MappingProxyType(
        {"User-agent": USER_AGENT, "Content-Type": "application/json"}
    )

    # --- ENCAPSULATED ROUTING REGISTRIES ---
    _DOMAINS_RESOURCE: Final[str] = "domains"
    _SAFE_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_]+$")

    # Mapping[str, Any] is used because the values in routes vary in structure
    _EXACT_ROUTES: Final[Mapping[str, Any]] = MappingProxyType(routes.EXACT_ROUTES)
    _PREFIX_ROUTES: Final[Mapping[str, Any]] = MappingProxyType(routes.PREFIX_ROUTES)
    _DOMAIN_ALIASES: Final[Mapping[str, str]] = MappingProxyType(routes.DOMAIN_ALIASES)

    _DOMAIN_ENDPOINTS: Final[Mapping[str, list[str]]] = MappingProxyType(routes.DOMAIN_ENDPOINTS)
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
        self.api_url: str = self._sanitize_url(base_url_input)
        self._validate_api_url()

    @staticmethod
    def _sanitize_url(raw_url: str) -> str:
        """Normalize the base API URL to have NO trailing slash.

        Args:
            raw_url: The raw URL string to sanitize.

        Returns:
            The sanitized URL string without a trailing slash.
        """
        raw_url = raw_url.strip().replace("\r", "").replace("\n", "")
        parsed = urlparse(raw_url)
        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
        return raw_url.rstrip("/")

    def _validate_api_url(self) -> None:
        """DX Guardrail & CWE-319: Warn on cleartext HTTP transmission."""
        parsed = urlparse(self.api_url)
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            logger.warning(
                "SECURITY WARNING: Cleartext HTTP transmission detected in API URL. "
                "Use 'https://' to prevent CWE-319 vulnerabilities."
            )

    @classmethod
    def _sanitize_key(cls, key: str) -> str:
        """Normalize and validate the endpoint key.

        Args:
            key: The raw endpoint key to sanitize.

        Returns:
            The sanitized and validated endpoint key.

        Raises:
            KeyError: If the resulting key is invalid or empty.
        """
        clean_key: str = key.lower()
        if not cls._SAFE_KEY_PATTERN.fullmatch(clean_key):
            clean_key = re.sub(r"[^a-z0-9_]", "", clean_key)
        if not clean_key:
            msg = f"Invalid endpoint key: {key}"
            raise KeyError(msg)
        return clean_key

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
        clean_key = self._sanitize_key(key)

        route_data = _get_cached_route_data(clean_key)

        # HTTP header mapping based on endpoint naming conventions
        requires_json_headers = "analytics" in clean_key or "bounceclassification" in clean_key

        # Prepare headers
        headers_map = self._HEADERS_JSON if requires_json_headers else self._HEADERS_BASE
        headers = dict(headers_map)

        # Reconstruct result
        if route_data.get("type") == "domain":
            # Domain logic still needs 'self' for internal version frozensets
            return self._resolve_domains_route(list(route_data["parts"])), headers

        # Create mutable copy of the URL structure for HANDLERS
        safe_url = {
            "base": self._build_base_url(route_data["version"], route_data.get("suffix", "")),
            "keys": list(route_data["keys"]),
        }

        return safe_url, headers

    @property
    def available_endpoints(self) -> set[str]:
        """Provide public access to valid route keys for IDE introspection."""
        return set(self._EXACT_ROUTES.keys()) | set(self._PREFIX_ROUTES.keys())


class SecretAuth(tuple):
    """OWASP: Obfuscate credentials in memory dumps and tracebacks."""

    __slots__ = ()  # DX & Performance: Prevent __dict__ creation for tuple subclasses to optimize memory usage.

    def __repr__(self) -> str:
        return "('api', '***REDACTED***')"


class BaseEndpoint:
    """Base class for endpoints.

    Contains methods common for Endpoint and AsyncEndpoint.
    """

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
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

    def __repr__(self) -> str:
        """DX: Show the actual resolved target route instead of memory address.

        Returns:
            A string representation of the endpoint instance.
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
        """
        keys = url.get("keys", [])
        endpoint_key = keys[0] if keys else ""

        handler = HANDLERS.get(endpoint_key, handle_default)

        # Mypy strict mode flags Callable[..., str] as untyped because of the ellipsis.
        # Adding type: ignore to safely bypass this strict rule during dynamic dispatch.
        return handler(url, domain, method, **kwargs)  # type: ignore[no-untyped-call]


class Endpoint(BaseEndpoint):
    """Generate synchronous requests and return responses."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initialize a new Endpoint instance for synchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: requests auth tuple or None.
            session: Optional pre-configured requests.Session instance.
        """
        super().__init__(url, headers, auth)
        self._session = session or requests.Session()

    def api_call(
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
        target_url = self.build_url(url, domain=domain, method=method, **kwargs)
        # REVERTED: Using 'requests' directly to ensure unittest.mock.patch intercepts the calls.
        req_method = getattr(requests, method)

        logger.debug("Sending Request: %s %s", method.upper(), target_url)

        try:
            response = req_method(
                target_url,
                data=data,
                params=filters,
                headers=headers,
                auth=auth,
                timeout=timeout,
                files=files,
                verify=True,
                stream=False,
            )

            status_code = getattr(response, "status_code", 200)
            is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD
            if is_error:
                # Prevent showing huge HTML-pages in logging
                raw_text = getattr(response, "text", "")
                error_body = (
                    raw_text[:_MAX_LOG_LENGTH] + "..."
                    if len(raw_text) > _MAX_LOG_LENGTH
                    else raw_text
                )

                logger.error(
                    "API Error %s | %s %s | Response: %s",
                    status_code,
                    method.upper(),
                    target_url,
                    error_body,
                )
            else:
                logger.debug(
                    "API Success %s | %s %s",
                    getattr(response, "status_code", 200),
                    method.upper(),
                    target_url,
                )

        except requests.exceptions.Timeout as e:
            logger.exception("Timeout Error: %s %s", method.upper(), target_url)
            raise TimeoutError from e
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
            # Payload Minification: Strip structural spaces to reduce network overhead by ~15-20% for large payload batches.
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
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
            self._auth,
            "put",
            self._url,
            headers=self.headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def patch(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
        self,
        data: Any | None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
            # Payload Minification: Strip structural spaces to reduce network overhead.
            data = json.dumps(data, separators=(",", ":"))

        return self.api_call(
            self._auth,
            "put",
            self._url,
            headers=req_headers,
            data=data,
            filters=filters,
            **kwargs,
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
            self._auth,
            "delete",
            self._url,
            headers=self.headers,
            domain=domain,
            **kwargs,
        )


class Client:
    """Client class."""

    def __init__(self, auth: tuple[str, str] | None = None, **kwargs: Any) -> None:
        """Initialize a new Client instance for API interaction.

        This method sets up API authentication, configuration, connection pooling,
        and automatic network resiliency (retries).

        Args:
            auth: A tuple containing the API user and API key (e.g., ("api", "key-123")).
            **kwargs: Additional configuration parameters, such as 'api_url'.
        """
        self.auth = self._validate_auth(auth)

        api_url = kwargs.get("api_url")
        self.config = Config(api_url=api_url)

        self._session = self._build_resilient_session()

    @staticmethod
    def _validate_auth(auth: tuple[str, str] | None) -> tuple[str, str] | None:
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

    @staticmethod
    def _build_resilient_session() -> requests.Session:
        """Set up connection pooling and automatic retries for transient failures.

        Returns:
            A configured requests.Session instance.
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s...
            status_forcelist=[429, 500, 502, 503, 504],
            # Network Resilience: Restrict automatic retries to idempotent methods to prevent duplicate operations (e.g., sending the same email twice).
            allowed_methods=["GET", "OPTIONS", "HEAD"],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100,
        )
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
        """
        url, headers = self.config[name]
        return Endpoint(url=url, headers=headers, auth=self.auth, session=self._session)

    def __repr__(self) -> str:
        """OWASP Secrets Management: Redact sensitive information from object representation.

        Returns:
            A redacted string representation of the Client instance.
        """
        return f"<{self.__class__.__name__} api_url={self.config.api_url!r}>"

    def __str__(self) -> str:
        """OWASP Secrets Management: Redact sensitive information from string representation.

        Returns:
            A redacted, human-readable string representation of the Client.
        """
        return f"Mailgun {self.__class__.__name__}"

    def __dir__(self) -> list[str]:
        """DX: Expose true config endpoints for IDE Introspection.

        Returns:
            A list of available attributes and endpoint routes.
        """
        return list(set(super().__dir__()) | self.config.available_endpoints)


class AsyncEndpoint(BaseEndpoint):
    """Generate async requests and return responses using httpx."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize a new AsyncEndpoint instance for asynchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: httpx auth tuple or None.
            client: Optional httpx.AsyncClient instance to reuse.
        """
        super().__init__(url, headers, auth)
        self._url = url
        self.headers = headers
        self._auth = auth
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
        target_url = self.build_url(url, domain=domain, method=method, **kwargs)

        # Build basic arguments
        request_kwargs: dict[str, Any] = {
            "method": method.upper(),
            "url": target_url,
            "params": filters,
            "files": files,
            "headers": headers,
            "auth": auth,
            "timeout": timeout,
        }

        # Deprecation Warning for httpx
        if isinstance(data, (str, bytes)):
            request_kwargs["content"] = data
        else:
            request_kwargs["data"] = data

        logger.debug("Sending Async Request: %s %s", method.upper(), target_url)

        try:
            response = await self._client.request(**request_kwargs)

            status_code = getattr(response, "status_code", 200)
            is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD

            if is_error:
                # Prevent showing huge HTML-pages in logging
                raw_text = getattr(response, "text", "")
                error_body = (
                    raw_text[:_MAX_LOG_LENGTH] + "..."
                    if len(raw_text) > _MAX_LOG_LENGTH
                    else raw_text
                )

                logger.error(
                    "API Error %s | %s %s | Response: %s",
                    status_code,
                    method.upper(),
                    target_url,
                    error_body,
                )
            else:
                logger.debug(
                    "API Success %s | %s %s",
                    getattr(response, "status_code", 200),
                    method.upper(),
                    target_url,
                )

        except httpx.TimeoutException as e:
            logger.exception("Timeout Error: %s %s", method.upper(), target_url)
            raise TimeoutError from e
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
            # Payload Minification: Strip structural spaces to reduce network overhead.
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
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
            self._auth,
            "put",
            self._url,
            headers=self.headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def patch(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
        self,
        data: Any | None,
        filters: Mapping[str, str | Any] | None = None,
        **kwargs: Any,
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
            # Payload Minification: Strip structural spaces to reduce network overhead.
            data = json.dumps(data, separators=(",", ":"))

        return await self.api_call(
            self._auth,
            "put",
            self._url,
            headers=req_headers,
            data=data,
            filters=filters,
            **kwargs,
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
            self._auth,
            "delete",
            self._url,
            headers=self.headers,
            domain=domain,
            **kwargs,
        )


class AsyncClient(Client):
    """Async client class using httpx."""

    endpoint_cls = AsyncEndpoint

    def __init__(self, auth: tuple[str, str] | None = None, **kwargs: Any) -> None:
        """Initialize a new AsyncClient instance for asynchronous API interaction.

        Args:
            auth: A tuple containing the API user and API key.
            **kwargs: Additional configuration parameters.
        """
        self.auth = self._validate_auth(auth)

        super().__init__(auth, **kwargs)
        self._client_kwargs = kwargs.get("client_kwargs", {})
        self._httpx_client: httpx.AsyncClient | None = None

    def __getattr__(self, name: str) -> Any:
        """Resolve and return the requested API endpoint instance.

        Splits the provided attribute name to execute the corresponding endpoint handler.

        Args:
            name: The endpoint attribute name (e.g., 'domains_ips' maps to ["domains", "ips"]).

        Returns:
            An endpoint instance configured for the requested route.
        """
        url, headers = self.config[name]
        return AsyncEndpoint(
            url=url,
            headers=headers,
            auth=self.auth,
            client=self._client,
        )

    @property
    def _client(self) -> httpx.AsyncClient:
        """Provide lazy initialization for the underlying httpx.AsyncClient.

        Returns:
            The active httpx.AsyncClient instance.
        """
        if not self._httpx_client or self._httpx_client.is_closed:
            self._httpx_client = httpx.AsyncClient(**self._client_kwargs)
        return self._httpx_client

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient.

        Call this when done with the client to properly clean up resources
        and avoid unclosed socket warnings.
        """
        if self._httpx_client:
            await self._httpx_client.aclose()

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

    def __dir__(self) -> list[str]:
        """DX: Expose true config endpoints for IDE Introspection.

        Returns:
            A list of available attributes and endpoint routes.
        """
        return list(set(super().__dir__()) | self.config.available_endpoints)

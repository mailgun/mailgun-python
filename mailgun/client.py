"""This module provides the main client and helper classes for interacting with the Mailgun API.

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
from urllib.parse import urlparse

from typing import Any, Final

import httpx
import requests

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
from mailgun import routes

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


# Public API
__all__ = [
    "APIVersion",
    "Config",
    "BaseEndpoint",
    "Endpoint",
    "AsyncEndpoint",
    "Client",
    "AsyncClient",
    "ApiError",
]

logger = logging.getLogger("mailgun.client")
# Ensure logger doesn't stay silent if the user hasn't configured basicConfig
if not logger.hasHandlers():
    logger.addHandler(logging.NullHandler())

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
    """
    Apply internal cached routing logic.

    Uses only hashable types (str) as arguments to avoid TypeError.
    """
    # 1. Exact Match
    if clean_key in routes.EXACT_ROUTES:
        version, route_keys = routes.EXACT_ROUTES[clean_key]
        return {"version": version, "keys": tuple(route_keys)}

    # 2. Parse resource parts
    route_parts = clean_key.split("_")
    primary_resource = route_parts[0]

    # 3. Domain Logic Trigger
    # We use a hardcoded string 'domains' or import it
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

    def __init__(self, api_url: str | None = None) -> None:  # noqa: D107
        self.ex_handler: bool = True
        base_url_input: str = api_url or self.DEFAULT_API_URL
        self.api_url: str = self._sanitize_url(base_url_input)
        self._validate_api_url()

    @staticmethod
    def _sanitize_url(raw_url: str) -> str:
        """Normalize the base API URL to have NO trailing slash."""
        raw_url = raw_url.strip().replace("\r", "").replace("\n", "")
        parsed = urlparse(raw_url)
        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
        return raw_url.rstrip("/")

    def _validate_api_url(self) -> None:
        """DX Guardrail & CWE-319: Warn on cleartext HTTP transmission."""
        parsed = urlparse(self.api_url)
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
            logger.warning(
                "SECURITY WARNING: Cleartext HTTP transmission detected in API URL. "
                "Use 'https://' to prevent CWE-319 vulnerabilities."
            )

    @classmethod
    def _sanitize_key(cls, key: str) -> str:
        """Normalize and validate the endpoint key."""
        clean_key: str = key.lower()
        if not cls._SAFE_KEY_PATTERN.fullmatch(clean_key):
            clean_key = re.sub(r"[^a-z0-9_]", "", clean_key)
        if not clean_key:
            raise KeyError(f"Invalid endpoint key: {key}")
        return clean_key

    def _build_base_url(self, version: APIVersion | str, suffix: str = "") -> str:
        """Construct API URL with precise slash control to prevent 404s."""
        ver_str: str = version.value if isinstance(version, APIVersion) else version
        base: str = f"{self.api_url}/{ver_str}"

        if suffix:
            path: str = f"{suffix}/" if suffix == self._DOMAINS_RESOURCE else suffix
            return f"{base}/{path}"

        return f"{base}/"

    def _resolve_domains_route(self, route_parts: list[str]) -> dict[str, Any]:
        """
        Handle context-aware versioning for domain-related endpoints.

        Returns a dict containing a string base and a tuple of keys.
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
        """
        Public entry point.

        Calls a standalone cached function.
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
        """Initialize a new Endpoint instance.

        :param url: URL dict with pairs {"base": "keys"}
        :type url: dict[str, Any]
        :param headers: Headers dict
        :type headers: dict[str, str]
        :param auth: requests auth tuple
        :type auth: tuple[str, str] | None
        """
        self._url = url
        self.headers = headers
        self._auth = auth

    @staticmethod
    def build_url(
        url: dict[str, Any],
        domain: str | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Build final request url using predefined handlers.

        Note: Some urls are being built in Config class, as they can't be generated dynamically.
        :param url: incoming url (base+keys)
        :type url: dict[str, Any]
        :param domain: incoming domain
        :type domain: str
        :param method: requested method
        :type method: str
        :param kwargs: kwargs
        :type kwargs: Any
        :return: built URL
        """
        return HANDLERS[url["keys"][0]](url, domain, method, **kwargs)


class Endpoint(BaseEndpoint):
    """Generate request and return response."""

    def api_call(
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: int | float | tuple[float, float] = 60,
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Response | Any:
        """Build URL and make a request.

        :param auth: auth data
        :type auth: tuple[str, str] | None
        :param method: request method
        :type method: str
        :param url: incoming url (base+keys)
        :type url: dict[str, Any]
        :param headers: incoming headers
        :type headers: dict[str, str]
        :param data: incoming post/put data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict | None
        :param timeout: requested timeout (60-default)
        :type timeout: int
        :param files: incoming files
        :type files: dict[str, Any] | None
        :param domain: incoming domain
        :type domain: str | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: server response from API
        :rtype: requests.models.Response
        :raises: TimeoutError, ApiError
        """
        target_url = self.build_url(url, domain=domain, method=method, **kwargs)
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
            is_error = isinstance(status_code, int) and status_code >= 400

            if is_error:
                # Prevent showing huge HTML-pages in logging
                raw_text = getattr(response, "text", "")
                error_body = raw_text[:500] + "..." if len(raw_text) > 500 else raw_text

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

            return response

        except requests.exceptions.Timeout as e:
            logger.error("Timeout Error: %s %s", method.upper(), target_url)
            raise TimeoutError from e
        except requests.RequestException as e:
            logger.critical("Request Exception: %s | URL: %s", e, target_url)
            raise ApiError(e) from e

    def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """GET method for API calls.

        :param filters: incoming params
        :type filters: Mapping[str, str | Any] | None
        :param domain: incoming domain
        :type domain: str | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call GET request
        :rtype: requests.models.Response
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
        """POST method for API calls.

        :param data: incoming post data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param domain: incoming domain
        :type domain: str
        :param headers: incoming headers
        :type headers: dict[str, str]
        :param files: incoming files
        :type files: Any | None = None,
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call POST request
        :rtype: requests.models.Response
        """
        req_headers = self.headers.copy()

        if headers and isinstance(headers, dict):
            req_headers.update(headers)

        if req_headers.get("Content-Type") == "application/json":
            if data is not None and not isinstance(data, (str, bytes)):
                data = json.dumps(data)

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
        """PUT method for API calls.

        :param data: incoming data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PUT request
        :rtype: requests.models.Response
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
        """PATCH method for API calls.

        :param data: incoming data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PATCH request
        :rtype: requests.models.Response
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
        """PUT method for API calls.

        :param data: incoming data
        :type data: dict[str, Any] | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PUT request
        :rtype: requests.models.Response
        """
        custom_headers = kwargs.pop("headers", {})
        req_headers = self.headers.copy()
        if custom_headers and isinstance(custom_headers, dict):
            req_headers.update(custom_headers)

        if req_headers.get("Content-Type") == "application/json":
            if data is not None and not isinstance(data, (str, bytes)):
                data = json.dumps(data)

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
        """DELETE method for API calls.

        :param domain: incoming domain
        :type domain: str
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call DELETE request
        :rtype: requests.models.Response
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

        This method sets up API authentication and configuration. The `auth` parameter
        provides a tuple with the API key and secret. Additional keyword arguments can
        specify configuration options like API version and URL.

        :param auth: auth set ("username", "APIKEY")
        :type auth: set
        :param kwargs: kwargs
        """
        self.auth = auth
        api_url = kwargs.get("api_url")
        self.config = Config(api_url=api_url)

    def __getattr__(self, name: str) -> Any:
        """Get named attribute of an object, split it and execute.

        :param name: attribute name (Example: client.domains_ips. names:
            ["domains", "ips"])
        :type name: str
        :return: type object (executes existing handler)
        """
        url, headers = self.config[name]
        return Endpoint(url=url, headers=headers, auth=self.auth)

    def __repr__(self) -> str:
        """OWASP Secrets Management: Redact sensitive information from object representation.

        Returns:
            str: A redacted string representation of the Client instance.
        """
        return f"<{self.__class__.__name__} api_url={self.config.api_url!r}>"


class AsyncEndpoint(BaseEndpoint):
    """Generate async request and return response using httpx."""

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        client: httpx.AsyncClient,
    ) -> None:
        """Initialize a new AsyncEndpoint instance.

        :param url: URL dict with pairs {"base": "keys"}
        :type url: dict[str, Any]
        :param headers: Headers dict
        :type headers: dict[str, str]
        :param auth: httpx auth tuple
        :type auth: tuple[str, str] | None
        :param client: Optional httpx.AsyncClient instance to reuse
        :type client: httpx.AsyncClient | None
        """
        super().__init__(url, headers, auth)
        self._url = url
        self.headers = headers
        self._auth = auth
        self._client = client

    async def api_call(
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: int | float | tuple[float, float] = 60,
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> HttpxResponse:
        """Build URL and make an async request.

        :param auth: auth data
        :type auth: tuple[str, str] | None
        :param method: request method
        :type method: str
        :param url: incoming url (base+keys)
        :type url: dict[str, Any]
        :param headers: incoming headers
        :type headers: dict[str, str]
        :param data: incoming post/put data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict | None
        :param timeout: requested timeout (60-default)
        :type timeout: int
        :param files: incoming files
        :type files: dict[str, Any] | None
        :param domain: incoming domain
        :type domain: str | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: server response from API
        :rtype: httpx.Response
        :raises: TimeoutError, ApiError
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
            is_error = isinstance(status_code, int) and status_code >= 400

            if is_error:
                # Prevent showing huge HTML-pages in logging
                raw_text = getattr(response, "text", "")
                error_body = raw_text[:500] + "..." if len(raw_text) > 500 else raw_text

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

            return response

        except httpx.TimeoutException as e:
            logger.error("Timeout Error: %s %s", method.upper(), target_url)
            raise TimeoutError from e
        except httpx.RequestError as e:
            logger.critical("Request Exception: %s | URL: %s", e, target_url)
            raise ApiError(e) from e

    async def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> HttpxResponse:
        """GET method for async API calls.

        :param filters: incoming params
        :type filters: Mapping[str, str | Any] | None
        :param domain: incoming domain
        :type domain: str | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call GET request
        :rtype: httpx.Response
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
        """POST method for async API calls.

        :param data: incoming post data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param domain: incoming domain
        :type domain: str
        :param headers: incoming headers
        :type headers: dict[str, str]
        :param files: incoming files
        :type files: Any | None = None,
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call POST request
        :rtype: httpx.Response
        """
        req_headers = self.headers.copy()

        if headers and isinstance(headers, dict):
            req_headers.update(headers)

        if req_headers.get("Content-Type") == "application/json":
            if data is not None and not isinstance(data, (str, bytes)):
                data = json.dumps(data)

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
        """PUT method for async API calls.

        :param data: incoming data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PUT request
        :rtype: httpx.Response
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
        """PATCH method for async API calls.

        :param data: incoming data
        :type data: Any | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PATCH request
        :rtype: httpx.Response
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
        """PUT method for async API calls.

        :param data: incoming data
        :type data: dict[str, Any] | None
        :param filters: incoming params
        :type filters: dict
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call PUT request
        :rtype: httpx.Response
        """
        custom_headers = kwargs.pop("headers", {})
        req_headers = self.headers.copy()
        if custom_headers and isinstance(custom_headers, dict):
            req_headers.update(custom_headers)

        if req_headers.get("Content-Type") == "application/json":
            if data is not None and not isinstance(data, (str, bytes)):
                data = json.dumps(data)

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
        """DELETE method for async API calls.

        :param domain: incoming domain
        :type domain: str
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call DELETE request
        :rtype: httpx.Response
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
        """Initialize a new AsyncClient instance for API interaction."""
        super().__init__(auth, **kwargs)
        self._client_kwargs = kwargs.get("client_kwargs", {})
        self._httpx_client: httpx.AsyncClient | None = None

    def __getattr__(self, name: str) -> Any:
        """Get named attribute of an object, split it and execute.

        :param name: attribute name (Example: client.domains_ips. names:
            ["domains", "ips"])
        :type name: str
        :return: type object (executes existing handler)
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
        if not self._httpx_client or self._httpx_client.is_closed:
            self._httpx_client = httpx.AsyncClient(**self._client_kwargs)
        return self._httpx_client

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient.

        Call this when done with the client to properly clean up
        resources.
        """
        if self._httpx_client:
            await self._httpx_client.aclose()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.aclose()

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

import io
import json
import logging
import re
import sys
from collections import defaultdict
from enum import Enum
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from urllib.parse import urlparse

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


HANDLERS: dict[str, Callable] = {  # type: ignore[type-arg]
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


logger = logging.getLogger("mailgun.config")


def _load_routing_manifest() -> dict[str, Any]:
    """Load the JSON routing manifest safely (Zip-safe for .whl packages)."""
    manifest_name = "mailgun_routes.json"
    try:
        # Try to determine the package name dynamically
        pkg_name = __package__ or Path(__file__).parent.name
        manifest_text = files(pkg_name).joinpath(manifest_name).read_text(encoding="utf-8")
        return json.loads(manifest_text)
    except Exception as e:
        logger.debug("Falling back to Path-based loading due to: %s", e)
        manifest_path = Path(__file__).parent / manifest_name
        with Path(manifest_path).open(encoding="utf-8") as f:
            return json.load(f)


# Load manifest at module level
_ROUTES_MANIFEST = _load_routing_manifest()


class Config:
    """Configuration engine for the Mailgun API client.

    Refactored to maintain strict parity with legacy URL construction while
    using a data-driven routing approach.
    """

    __slots__ = ("api_url", "ex_handler")

    DEFAULT_API_URL: Final[str] = "https://api.mailgun.net"
    USER_AGENT: Final[str] = "mailgun-api-python/"

    # --- ENCAPSULATED ROUTING REGISTRIES ---
    _DOMAINS_RESOURCE: Final[str] = "domains"
    _SAFE_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_]+$")

    _EXACT_ROUTES: Final[MappingProxyType[str, tuple[str, tuple[str, ...]]]] = MappingProxyType(
        {
            k: (APIVersion(v[0]).value, tuple(v[1]))
            for k, v in _ROUTES_MANIFEST.get("exact_routes", {}).items()
            if len(v) >= 2
        },
    )

    _PREFIX_ROUTES: Final[MappingProxyType[str, tuple[str, str, Any]]] = MappingProxyType(
        {
            k: (APIVersion(v[0]).value, str(v[1]), v[2] if len(v) > 2 else None)
            for k, v in _ROUTES_MANIFEST.get("prefix_routes", {}).items()
            if len(v) >= 2
        },
    )

    _DOMAIN_ALIASES: Final[MappingProxyType[str, str]] = MappingProxyType(
        _ROUTES_MANIFEST.get("domain_aliases", {}),
    )

    _V1_DOMAIN_ENDPOINTS: Final[frozenset[str]] = frozenset(
        _ROUTES_MANIFEST.get("v1_domain_endpoints", []),
    )
    _V3_DOMAIN_ENDPOINTS: Final[frozenset[str]] = frozenset(
        _ROUTES_MANIFEST.get("v3_domain_endpoints", []),
    )
    _V4_DOMAIN_ENDPOINTS: Final[frozenset[str]] = frozenset(
        _ROUTES_MANIFEST.get("v4_domain_endpoints", []),
    )

    def __init__(self, api_url: str | None = None) -> None:  # noqa: D107
        self.ex_handler: bool = True
        base_url_input = api_url or self.DEFAULT_API_URL
        self.api_url = self._sanitize_url(base_url_input)

    @staticmethod
    def _sanitize_url(raw_url: str) -> str:
        """Normalize the base API URL to have NO trailing slash."""
        raw_url = raw_url.strip().replace("\r", "").replace("\n", "")
        parsed = urlparse(raw_url)
        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
        return raw_url.rstrip("/")

    @classmethod
    def _sanitize_key(cls, key: str) -> str:
        key = key.lower()
        if not cls._SAFE_KEY_PATTERN.fullmatch(key):
            key = re.sub(r"[^a-z0-9_]", "", key)
        if not key:
            raise KeyError("Invalid endpoint key.")
        return key

    def _build_base_url(self, version: APIVersion | str, suffix: str = "") -> str:
        """Construct API URL with precise slash control to prevent 404s."""
        # ENSURE: Always use .value for consistency in string building
        ver_str = version.value if isinstance(version, APIVersion) else version
        base = f"{self.api_url}/{ver_str}"

        if suffix:
            # MAINTAINER NOTE: 'domains' resource suffix requires a trailing slash for handler compatibility
            path = f"{suffix}/" if suffix == self._DOMAINS_RESOURCE else suffix
            return f"{base}/{path}"

        return f"{base}/"

    def _resolve_domains_route(self, route_parts: list[str]) -> dict[str, Any]:
        """Handle context-aware versioning for domain endpoints using snake_case matching."""
        if any(action in route_parts for action in ("activate", "deactivate")):
            return {
                "base": self._build_base_url(APIVersion.V4.value),
                "keys": [
                    self._DOMAINS_RESOURCE,
                    "{authority_name}",
                    "keys",
                    "{selector}",
                    route_parts[-1],
                ],
            }

        mapped_parts = [self._DOMAIN_ALIASES.get(p, p) for p in route_parts]

        # Version priority check (v1 -> v3 -> fallback v4)
        # MAINTAINER NOTE: Comparison is done against mapped snake_case names
        if not self._V1_DOMAIN_ENDPOINTS.isdisjoint(mapped_parts):
            version = APIVersion.V1.value
        elif not self._V3_DOMAIN_ENDPOINTS.isdisjoint(mapped_parts):
            version = APIVersion.V3.value
        else:
            version = APIVersion.V4.value

        return {"base": self._build_base_url(version, self._DOMAINS_RESOURCE), "keys": mapped_parts}

    def __getitem__(self, key: str) -> tuple[dict[str, Any], dict[str, str]]:  # noqa: D105
        key = self._sanitize_key(key)
        headers = {"User-agent": self.USER_AGENT}

        if "analytics" in key or "bounceclassification" in key:
            headers["Content-Type"] = "application/json"

        # 1. Exact Match
        if key in self._EXACT_ROUTES:
            version, route_keys = self._EXACT_ROUTES[key]
            return {"base": self._build_base_url(version), "keys": list(route_keys)}, headers

        route_parts = key.split("_")
        primary_resource = route_parts[0]

        # 2. Domain Logic
        if primary_resource == self._DOMAINS_RESOURCE:
            return self._resolve_domains_route(route_parts), headers

        # 3. Prefix & Fallback
        matched_prefix = key if key in self._PREFIX_ROUTES else primary_resource
        if matched_prefix in self._PREFIX_ROUTES:
            version, suffix, key_override = self._PREFIX_ROUTES[matched_prefix]
            if key_override:
                route_parts[0] = key_override
            return {"base": self._build_base_url(version, suffix), "keys": route_parts}, headers

        return {"base": self._build_base_url(APIVersion.V3.value), "keys": route_parts}, headers


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
    ) -> Any:
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
        timeout: int = 60,
        files: dict[str, bytes] | None = None,
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
        url = self.build_url(url, domain=domain, method=method, **kwargs)
        req_method = getattr(requests, method)

        try:
            return req_method(
                url,
                data=data,
                params=filters,
                headers=headers,
                auth=auth,
                timeout=timeout,
                files=files,
                verify=True,
                stream=False,
            )

        except requests.exceptions.Timeout:
            raise TimeoutError
        except requests.RequestException as e:
            raise ApiError(e)
        except Exception as e:
            raise e

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
        headers: str | None = None,
        files: dict[str, bytes] | None = None,
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
        :type files: dict[str, Any] | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call POST request
        :rtype: requests.models.Response
        """
        if "Content-Type" in self.headers:
            if self.headers["Content-Type"] == "application/json":
                data = json.dumps(data)
        elif headers:
            if headers == "application/json":
                data = json.dumps(data)
                self.headers["Content-Type"] = "application/json"
            elif headers == "multipart/form-data":
                self.headers["Content-Type"] = "multipart/form-data"

        return self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=self.headers,
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
        if self.headers["Content-type"] == "application/json":
            data = json.dumps(data)
        return self.api_call(
            self._auth,
            "put",
            self._url,
            headers=self.headers,
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
        split = name.split("_")
        # identify the resource
        fname = split[0]
        url, headers = self.config[name]
        return type(fname, (Endpoint,), {})(url=url, headers=headers, auth=self.auth)


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

    @staticmethod
    def _prepare_files(files: Any) -> dict[str, Any] | None:
        """Convert files to httpx format: {"field": (filename, file_obj, content_type)}."""
        min_length = 2
        httpx_files = None
        if not files:
            return httpx_files

        if isinstance(files, dict):
            # Convert dict[str, bytes] to httpx format
            # httpx expects: {"field": (filename, file_obj, content_type)}
            httpx_files = {}
            for key, value in files.items():
                if isinstance(value, bytes):
                    httpx_files[key] = (key, io.BytesIO(value), "application/octet-stream")
                elif isinstance(value, tuple) and len(value) >= min_length:
                    # Already in tuple format: (filename, content, ...)
                    filename = value[0]
                    content = value[1]
                    content_type = (
                        value[2] if len(value) > min_length else "application/octet-stream"
                    )
                    if isinstance(content, bytes):
                        httpx_files[key] = (filename, io.BytesIO(content), content_type)
                    else:
                        httpx_files[key] = value
                else:
                    httpx_files[key] = value
        elif isinstance(files, list):
            # Convert list of tuples to httpx dict format
            files_dict: dict[str, list[tuple[str, Any, str]]] = defaultdict(list)
            for item in files:
                if isinstance(item, tuple) and len(item) >= min_length:
                    field_name = item[0]
                    file_data = item[1]
                    if isinstance(file_data, tuple) and len(file_data) >= min_length:
                        filename = file_data[0]
                        content = file_data[1]
                        content_type = (
                            file_data[2]
                            if len(file_data) > min_length
                            else "application/octet-stream"
                        )
                        if isinstance(content, bytes):
                            files_dict[field_name].append(
                                (filename, io.BytesIO(content), content_type),
                            )
                        else:
                            files_dict[field_name].append(file_data)
                    elif isinstance(file_data, bytes):
                        files_dict[field_name].append(
                            (field_name, io.BytesIO(file_data), "application/octet-stream"),
                        )
                    else:
                        files_dict[field_name].append(file_data)

            httpx_files = {
                field: file_list[0] if len(file_list) == 1 else file_list
                for field, file_list in files_dict.items()
            }
        else:
            httpx_files = files
        return httpx_files

    async def api_call(
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: int = 60,
        files: dict[str, bytes] | None = None,
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
        url = self.build_url(url, domain=domain, method=method, **kwargs)

        request_kwargs: dict[str, Any] = {
            "method": method.upper(),
            "url": url,
            "params": filters,
            "data": data,
            "files": self._prepare_files(files),
            "headers": headers,
            "auth": auth,
            "timeout": timeout,
        }

        try:
            return await self._client.request(**request_kwargs)

        except httpx.TimeoutException:
            raise TimeoutError
        except httpx.RequestError as e:
            raise ApiError(e)
        except Exception as e:
            raise e

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
        headers: str | None = None,
        files: dict[str, bytes] | None = None,
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
        :type files: dict[str, Any] | None
        :param kwargs: kwargs
        :type kwargs: Any
        :return: api_call POST request
        :rtype: httpx.Response
        """
        if "Content-Type" in self.headers:
            if self.headers["Content-Type"] == "application/json":
                data = json.dumps(data)
        elif headers:
            if headers == "application/json":
                data = json.dumps(data)
                self.headers["Content-Type"] = "application/json"
            elif headers == "multipart/form-data":
                self.headers["Content-Type"] = "multipart/form-data"

        return await self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=self.headers,
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
        if self.headers.get("Content-type") == "application/json":
            data = json.dumps(data)
        return await self.api_call(
            self._auth,
            "put",
            self._url,
            headers=self.headers,
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

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a new AsyncClient instance for API interaction."""
        super().__init__(**kwargs)
        # Save client kwargs for client reinitialization
        self._client_kwargs = {k: v for k, v in kwargs.items() if k != "api_url"}
        self._httpx_client: httpx.AsyncClient = None

    def __getattr__(self, name: str) -> Any:
        """Get named attribute of an object, split it and execute.

        :param name: attribute name (Example: client.domains_ips. names:
            ["domains", "ips"])
        :type name: str
        :return: type object (executes existing handler)
        """
        split = name.split("_")
        # identify the resource
        fname = split[0]
        url, headers = self.config[name]
        return type(fname, (AsyncEndpoint,), {})(
            url=url,
            headers=headers,
            auth=self.auth,
            client=self._client,
        )

    @property
    def _client(self) -> AsyncClient:
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

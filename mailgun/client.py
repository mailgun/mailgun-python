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
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urljoin

import httpx
import requests

from mailgun.handlers.bounce_classification_handler import handle_bounce_classification
from mailgun.handlers.default_handler import handle_default
from mailgun.handlers.domains_handler import handle_domainlist
from mailgun.handlers.domains_handler import handle_domains
from mailgun.handlers.domains_handler import handle_sending_queues
from mailgun.handlers.email_validation_handler import handle_address_validate
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.inbox_placement_handler import handle_inbox
from mailgun.handlers.ip_pools_handler import handle_ippools
from mailgun.handlers.ips_handler import handle_ips
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


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from httpx import Response as HttpxResponse
    from requests.models import Response


HANDLERS: dict[str, Callable] = {  # type: ignore[type-arg]
    "resendmessage": handle_resend_message,
    "domains": handle_domains,
    "domainlist": handle_domainlist,
    "dkim_authority": handle_domains,
    "dkim_selector": handle_domains,
    "web_prefix": handle_domains,
    "sending_queues": handle_sending_queues,
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
}


class Config:
    """Config class. Configure client with basic (urls, version, headers)."""

    DEFAULT_API_URL: str = "https://api.mailgun.net/"
    API_REF: str = "https://documentation.mailgun.com/en/latest/api_reference.html"
    user_agent: str = "mailgun-api-python/"

    def __init__(self, api_url: str | None = None) -> None:
        """Initialize a new Config instance with specified or default API settings.

        This initializer sets the API version and base URL. If no version or URL
        is provided, it defaults to the predefined class values.

        :param version: API version (default: v3)
        :type version: str | None
        :param api_url: API base url
        :type api_url: str | None
        """
        self.ex_handler: bool = True
        self.api_url = api_url or self.DEFAULT_API_URL

    def __getitem__(self, key: str) -> tuple[Any, dict[str, str]]:
        """Parse incoming split attr name, check it and prepare endpoint url.

        Most urls generated here can't be generated dynamically as we are doing this
        in build_url() method under Endpoint class.
        :param key: incoming attr name
        :type key: str
        :return: url, headers
        """
        key = key.lower()
        headers = {"User-agent": self.user_agent}
        v1_base = urljoin(self.api_url, "v1/")
        v2_base = urljoin(self.api_url, "v2/")
        v3_base = urljoin(self.api_url, "v3/")
        v4_base = urljoin(self.api_url, "v4/")
        v5_base = urljoin(self.api_url, "v5/")

        special_cases = {
            "messages": {"base": v3_base, "keys": ["messages"]},
            "mimemessage": {"base": v3_base, "keys": ["messages.mime"]},
            "resendmessage": {"base": v3_base, "keys": ["resendmessage"]},
            "ippools": {"base": v3_base, "keys": ["ip_pools"]},
            "dkimkeys": {"base": v1_base, "keys": ["dkim", "keys"]},
            "domainlist": {"base": v4_base, "keys": ["domainlist"]},
            # /v1/analytics/metrics
            # /v1/analytics/usage/metrics
            # /v1/analytics/logs
            # /v1/analytics/tags
            # /v1/analytics/tags/limits
            "analytics": {
                "base": v1_base,
                "keys": ["analytics", "usage", "metrics", "logs", "tags", "limits"],
            },
            # /v2/bounce-classification/metrics
            "bounceclassification": {
                "base": v2_base,
                "keys": ["bounce-classification", "metrics"],
            },
        }

        if key in special_cases:
            return special_cases[key], headers

        if "analytics" in key:
            headers |= {"Content-Type": "application/json"}
            return {
                "base": v1_base,
                "keys": key.split("_"),
            }, headers

        if "bounceclassification" in key:
            headers |= {"Content-Type": "application/json"}
            part1 = key[:6]
            part2 = key[6:]
            return {
                "base": v2_base,
                "keys": f"{part1}-{part2}".split("_"),
            }, headers

        # Handle DIPP endpoints
        if "subaccount" in key:
            if "ip_pools" in key:
                return {
                    "base": v5_base,
                    "keys": ["accounts", "subaccounts", "ip_pools"],
                }, headers
            if "ip_pool" in key:
                return {
                    "base": v5_base,
                    "keys": ["accounts", "subaccounts", "{subaccountId}", "ip_pool"],
                }, headers

        # Handle DKIM management endpoints
        if "dkim_management" in key:
            if "rotation" in key:
                return {
                    "base": v1_base,
                    "keys": ["dkim_management", "domains", "{name}", "rotation"],
                }, headers
            if "rotate" in key:
                return {
                    "base": v1_base,
                    "keys": ["dkim_management", "domains", "{name}", "rotate"],
                }, headers

        if "domains" in key:
            split = key.split("_") if "_" in key else [key]
            final_keys = split

            if any(x in key for x in ("activate", "deactivate")):
                action = "activate" if "activate" in key else "deactivate"
                final_keys = [
                    "domains",
                    "{authority_name}",
                    "keys",
                    "{selector}",
                    action,
                ]
                return {"base": v4_base, "keys": final_keys}, headers

            if "dkimauthority" in split:
                final_keys = ["dkim_authority"]
            elif "dkimselector" in split:
                final_keys = ["dkim_selector"]
            elif "webprefix" in split:
                final_keys = ["web_prefix"]
            elif "sendingqueues" in split:
                final_keys = ["sending_queues"]

            v3_domain_endpoints = {
                "credentials",
                "connection",
                "tracking",
                "dkimauthority",
                "dkimselector",
                "webprefix",
                "webhooks",
                "sendingqueues",
            }
            base = v3_base if any(x in key for x in v3_domain_endpoints) else v4_base
            return {"base": f"{base}domains/", "keys": final_keys}, headers

        if "addressvalidate" in key:
            return {
                "base": f"{v4_base}address/validate",
                "keys": key.split("_"),
            }, headers

        return {"base": v3_base, "keys": key.split("_")}, headers


class BaseEndpoint:
    """Base class for endpoints. Contains methods common for Endpoint and AsyncEndpoint."""

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

        :param name: attribute name (Example: client.domains_ips. names: ["domains", "ips"])
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
        client: httpx.AsyncClient | None = None,
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
    def _prepare_files(files: dict[str, str] | None) -> dict[str, str]:
        """Convert files to httpx format: {"field": (filename, file_obj, content_type)}."""
        httpx_files = None
        if files:
            import io
            from collections import defaultdict

            if isinstance(files, dict):
                # Convert dict[str, bytes] to httpx format
                # httpx expects: {"field": (filename, file_obj, content_type)}
                httpx_files = {}
                for key, value in files.items():
                    if isinstance(value, bytes):
                        httpx_files[key] = (key, io.BytesIO(value), "application/octet-stream")
                    elif isinstance(value, tuple) and len(value) >= 2:
                        # Already in tuple format: (filename, content, ...)
                        filename = value[0]
                        content = value[1]
                        content_type = value[2] if len(value) > 2 else "application/octet-stream"
                        if isinstance(content, bytes):
                            httpx_files[key] = (filename, io.BytesIO(content), content_type)
                        else:
                            httpx_files[key] = value
                    else:
                        httpx_files[key] = value
            elif isinstance(files, list):
                # Convert list of tuples to httpx dict format
                # Input: [("field", (filename, bytes)), ...] or [("field", ("filename", bytes)), ...]
                # Output: {"field": [(filename, file_obj, content_type), ...]} for multiple files
                #         or {"field": (filename, file_obj, content_type)} for single file
                files_dict: dict[str, list[tuple[str, Any, str]]] = defaultdict(list)
                for item in files:
                    if isinstance(item, tuple) and len(item) >= 2:
                        field_name = item[0]
                        file_data = item[1]
                        if isinstance(file_data, tuple) and len(file_data) >= 2:
                            filename = file_data[0]
                            content = file_data[1]
                            content_type = (
                                file_data[2] if len(file_data) > 2 else "application/octet-stream"
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
        if (
            self.headers.get("Content-type") == "application/json"
            or self.headers.get("Content-Type") == "application/json"
        ):
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

    def __init__(self, **kwargs: Any):
        """Initialize a new AsyncClient instance for API interaction."""
        super().__init__(**kwargs)
        # Save client kwargs for client reinitialization
        self._client_kwargs = {k: v for k, v in kwargs.items() if k not in ("api_url",)}
        self._httpx_client = None

    def __getattr__(self, name: str) -> Any:
        """Get named attribute of an object, split it and execute.

        :param name: attribute name (Example: client.domains_ips. names: ["domains", "ips"])
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

        Call this when done with the client to properly clean up resources.
        """
        if self._httpx_client:
            await self._httpx_client.aclose()

    async def __aenter__(self) -> AsyncClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.aclose()

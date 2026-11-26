from __future__ import annotations

import asyncio
import importlib
import json
import sys
import time
import warnings
from functools import lru_cache
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import parse_qs, urlparse

import requests  # pyright: ignore[reportMissingModuleSource]
from requests.models import Response  # pyright: ignore[reportMissingModuleSource]

from mailgun import routes
from mailgun.config import RetryPolicy
from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError
from mailgun.logger import get_logger
from mailgun.security import SecurityGuard


httpx2: Any
try:
    import httpx2 as _httpx2_runtime

    httpx2 = _httpx2_runtime
except ImportError:  # pragma: no cover
    httpx2 = None


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    import httpx2 as _httpx2_mod

    from mailgun.types import APIResponseType, AsyncAPIResponseType, TimeoutType


logger = get_logger(__name__)

_HTTP_ERROR_THRESHOLD: Final[int] = 400


def build_path_from_keys(keys: Iterable[str]) -> str:
    """Convert a sequence of endpoint keys into a URL path string.

    Args:
        keys: An iterable of string components for the URL path.

    Returns:
        A formatted path string starting with a slash, or an empty string if the iterable is empty.
    """
    if not keys:
        return ""
    keys_seq = keys if isinstance(keys, (list, tuple)) else list(keys)
    # Safely evaluate truthiness to prevent dropping `0` integer IDs
    return "".join(
        f"/{SecurityGuard.sanitize_path_segment(str(k))}"
        for k in keys_seq
        if k is not None and str(k).strip()
    )


_HANDLER_REGISTRY: Final[dict[str, tuple[str, str]]] = {
    "domains": ("mailgun.handlers.domains_handler", "handle_domains"),
    "dkim_authority": ("mailgun.handlers.domains_handler", "handle_domains"),
    "dkim_selector": ("mailgun.handlers.domains_handler", "handle_domains"),
    "web_prefix": ("mailgun.handlers.domains_handler", "handle_domains"),
    "domainlist": ("mailgun.handlers.domains_handler", "handle_domainlist"),
    "dkim": ("mailgun.handlers.domains_handler", "handle_dkimkeys"),
    "sending_queues": ("mailgun.handlers.domains_handler", "handle_sending_queues"),
    "mailboxes": ("mailgun.handlers.domains_handler", "handle_mailboxes_credentials"),
    "webhooks": ("mailgun.handlers.domains_handler", "handle_webhooks"),
    "bounces": ("mailgun.handlers.suppressions_handler", "handle_bounces"),
    "unsubscribes": ("mailgun.handlers.suppressions_handler", "handle_unsubscribes"),
    "whitelists": ("mailgun.handlers.suppressions_handler", "handle_whitelists"),
    "complaints": ("mailgun.handlers.suppressions_handler", "handle_complaints"),
    "resendmessage": ("mailgun.handlers.messages_handler", "handle_resend_message"),
    "ips": ("mailgun.handlers.ips_handler", "handle_ips"),
    "ip_pools": ("mailgun.handlers.ip_pools_handler", "handle_ippools"),
    "tags": ("mailgun.handlers.tags_handler", "handle_tags"),
    "routes": ("mailgun.handlers.routes_handler", "handle_routes"),
    "lists": ("mailgun.handlers.mailinglists_handler", "handle_lists"),
    "templates": ("mailgun.handlers.templates_handler", "handle_templates"),
    "address": ("mailgun.handlers.email_validation_handler", "handle_address_validate"),
    "addressvalidate": ("mailgun.handlers.email_validation_handler", "handle_address_validate"),
    "address_bulk": ("mailgun.handlers.email_validation_handler", "handle_address_validate"),
    "address_preview": ("mailgun.handlers.email_validation_handler", "handle_address_validate"),
    "address_validate": ("mailgun.handlers.email_validation_handler", "handle_address_validate"),
    "inbox": ("mailgun.handlers.inbox_placement_handler", "handle_inbox"),
    "analytics": ("mailgun.handlers.metrics_handler", "handle_metrics"),
    "bounce-classification": (
        "mailgun.handlers.bounce_classification_handler",
        "handle_bounce_classification",
    ),
    "users": ("mailgun.handlers.users_handler", "handle_users"),
    "keys": ("mailgun.handlers.keys_handler", "handle_keys"),
}


@lru_cache(maxsize=32)
def _load_handler(endpoint_key: str) -> Callable[..., str]:
    """Lazy load the API URL handler for a specific endpoint via declarative dispatch.

    Returns:
        Callable: The specific handler function for the requested endpoint.
    """
    module_name, attr_name = _HANDLER_REGISTRY.get(
        endpoint_key,
        ("mailgun.handlers.default_handler", "handle_default"),
    )
    return getattr(importlib.import_module(module_name), attr_name)


class BaseEndpoint:
    """Base class for endpoints. Contains methods common for Endpoint and AsyncEndpoint."""

    __slots__ = ("_auth", "_timeout", "_url", "dry_run", "headers", "retry_policy")

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        timeout: TimeoutType = 60,
        *,
        dry_run: bool = False,
    ) -> None:
        """Initialize a new BaseEndpoint instance.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: Authentication tuple or None.
            timeout: Base request timeout.
            dry_run: Execution sandbox flag to prevent I/O.
        """
        self._url = url
        self.headers = headers
        self._auth = auth
        self._timeout = timeout
        self.dry_run = dry_run
        self.retry_policy: RetryPolicy | None = None

    @staticmethod
    def _warn_if_deprecated(method: str, target_url: str) -> None:
        """Check the formulated URL against the registry of deprecated endpoints.

        Issues both a standard Python DeprecationWarning and an SDK logger warning.

        Args:
            method: Requested HTTP method.
            target_url: Formulated destination URL.
        """
        path = urlparse(target_url).path

        # Iterate over the dynamically compiled, cached regexes
        for pattern, msg in routes.get_deprecated_regexes().items():
            if pattern.search(path):
                warning_message = f"DEPRECATED API CALL ({method.upper()} {path}): {msg}"
                warnings.warn(warning_message, DeprecationWarning, stacklevel=3)
                logger.warning(warning_message)
                break

    @staticmethod
    def _reset_stream_pointers(files: Any) -> None:
        """Ensure the idempotency of file generators and buffers during retries."""
        if not isinstance(files, list):
            return
        for _, file_tuple in files:
            if isinstance(file_tuple, tuple) and len(file_tuple) >= 2:  # noqa: PLR2004
                file_obj = file_tuple[1]
                # If it's our ChunkedStreamer, close current FD, so __iter__ open it again
                if hasattr(file_obj, "close") and hasattr(file_obj, "chunk_size"):
                    file_obj.close()
                # If it's BytesIO or an opened file
                elif hasattr(file_obj, "seek"):
                    file_obj.seek(0)

    @staticmethod
    def _prepare_payload(
        data: Any | None,
        files: Any | None,
        headers: dict[str, str],
    ) -> tuple[Any | None, dict[str, str]]:
        """Prepares headers and minifies JSON payloads or handles multipart files safely.

        Args:
            data: Payload data (form data or JSON).
            files: Files to upload.
            headers: Request headers.

        Returns:
            A tuple containing the prepared data and working headers.
        """
        working_headers = dict(headers)
        if files and working_headers:
            working_headers = {
                k: v for k, v in working_headers.items() if k.lower() != "content-type"
            }

        is_json_request = any(
            k.lower() == "content-type" and "application/json" in str(v).lower()
            for k, v in working_headers.items()
        )

        if is_json_request and data is not None and not isinstance(data, (str, bytes)):
            data = json.dumps(data, separators=(",", ":"), default=str)

        return data, working_headers

    @staticmethod
    def _handle_api_error(e: Exception, method: str, target_url: str) -> None:
        """Encapsulates low-level transport exceptions into custom SDK errors.

        Args:
            e: The caught exception.
            method: The HTTP method.
            target_url: The target URL.

        Raises:
            MailgunTimeoutError: If the request times out.
            ApiError: If network routing fails or the API request fails.
        """
        timeout_errors: tuple[type[BaseException], ...] = (
            (requests.Timeout, httpx2.TimeoutException)
            if httpx2 is not None
            else (requests.Timeout,)
        )
        network_errors: tuple[type[BaseException], ...] = (
            (requests.ConnectionError, httpx2.ConnectError, httpx2.NetworkError)
            if httpx2 is not None
            else (requests.ConnectionError,)
        )
        if isinstance(e, timeout_errors):
            msg = f"Request timed out for {method.upper()} {target_url}"
            raise MailgunTimeoutError(msg) from e
        if isinstance(e, ApiError):
            raise e
        if isinstance(e, network_errors):
            msg = f"Network routing failed for {method.upper()} {target_url}: {e}"
            raise ApiError(msg) from e
        msg = f"API request failed for {method.upper()} {target_url}: {e}"
        raise ApiError(msg) from e

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

        # Load the handler function dynamically via the cached lazy loader
        handler = _load_handler(endpoint_key)

        return handler(url, domain, method, **kwargs)

    def _merge_headers(self, kwargs: dict[str, Any]) -> dict[str, str]:
        """Safely extract and merge custom headers from kwargs.

        Returns:
            A dictionary containing the safely merged headers.
        """
        custom_headers = kwargs.pop("headers", {})
        req_headers = self.headers.copy()

        if custom_headers and isinstance(custom_headers, dict):
            req_headers.update(custom_headers)

        # CWE-400 / Crash Prevention: Enforce string keys and values to
        # prevent HTTP protocol serialization crashes in requests/httpx2.
        return {str(k): str(v) for k, v in req_headers.items()}

    def _prepare_request(
        self,
        method: str,
        url: dict[str, Any],
        domain: str | None,
        timeout: TimeoutType,
        headers: dict[str, str],
        kwargs: dict[str, Any],
    ) -> tuple[str, str, str, TimeoutType, dict[str, str], dict[str, Any]]:
        """Security and routing preparation logic.

        Args:
            method: The requested HTTP method.
            url: Incoming URL structure containing base and keys.
            domain: Target domain name to sanitize.
            timeout: Request timeout duration.
            headers: Headers dictionary.
            kwargs: Additional keyword arguments.

        Returns:
            A tuple containing safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, and safe_kwargs.
        """
        safe_method = SecurityGuard.sanitize_http_method(method)
        safe_kwargs = SecurityGuard.filter_safe_kwargs(kwargs)
        safe_headers = SecurityGuard.sanitize_headers(headers) or {}
        target_domain = SecurityGuard.sanitize_domain(domain)
        target_domain_normalized = SecurityGuard.normalize_domain(target_domain)

        actual_timeout = timeout if timeout is not None else self._timeout
        safe_timeout = SecurityGuard.sanitize_timeout(actual_timeout)

        target_url = self.build_url(
            url,
            domain=target_domain_normalized,
            method=safe_method,
            **kwargs,
        )
        self._warn_if_deprecated(safe_method, target_url)

        # PEP 578 and protection against Log Forging (CWE-117)
        safe_url_for_log = SecurityGuard.sanitize_log_trace(target_url)

        return safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs

    @staticmethod
    def _cast_query_param(orig_ref: Any, raw_values: list[str]) -> Any:
        """Cast query string values to match the original filter parameter type.

        Args:
            orig_ref: Reference value indicating the intended target type.
            raw_values: List of string values extracted from the URL query string.

        Returns:
            The parsed value cast to bool, int, float, list, tuple, set, or str.
        """
        parsed_str = raw_values[0] if len(raw_values) == 1 else raw_values

        if isinstance(orig_ref, bool):
            return str(raw_values[0]).lower() in {"true", "1", "yes"}
        if isinstance(orig_ref, int):
            return int(raw_values[0])
        if isinstance(orig_ref, float):
            return float(raw_values[0])
        if isinstance(orig_ref, list):
            return raw_values
        if isinstance(orig_ref, tuple):
            return tuple(raw_values)
        if isinstance(orig_ref, set):
            return set(raw_values)
        return parsed_str

    @staticmethod
    def _compute_retry_delay(
        policy: RetryPolicy,
        status_code: int,
        response: Any,
        attempt: int,
    ) -> float:
        """Compute retry delay respecting Retry-After on HTTP 429 responses.

        Returns:
            float: Delay duration in seconds before the next retry attempt.
        """
        delay = policy.calculate_delay(attempt)
        if status_code == HTTPStatus.TOO_MANY_REQUESTS and policy.respect_retry_after:
            headers = getattr(response, "headers", None)
            retry_after = headers.get("Retry-After") if headers is not None else None
            if retry_after and str(retry_after).isdigit():
                delay = min(float(retry_after), policy.max_delay)
        return delay

    @staticmethod
    def _log_response_status(
        status_code: Any,
        safe_method: str,
        safe_url_for_log: str,
        *,
        is_async: bool = False,
    ) -> None:
        """Emit structured debug/error logs for completed API responses."""
        if isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD:
            msg = "API Async Error %s | %s %s" if is_async else "API Error %s | %s %s"
            logger.error(msg, status_code, safe_method.upper(), safe_url_for_log)
        else:
            msg = "API Async Success %s | %s %s" if is_async else "API Success %s | %s %s"
            logger.debug(msg, status_code, safe_method.upper(), safe_url_for_log)

    @classmethod
    def _advance_pagination_filters(
        cls,
        next_url: str,
        initial_filters: dict[str, Any],
        current_filters: dict[str, Any],
    ) -> None:
        """Update pagination query filters in-place from Mailgun's ``paging.next`` URL."""
        query_params = parse_qs(urlparse(next_url).query)
        for k, v in query_params.items():
            if not v:
                continue
            orig_ref = initial_filters.get(k, current_filters.get(k))
            if orig_ref is not None:
                current_filters[k] = cls._cast_query_param(orig_ref, v)
            else:
                current_filters[k] = v[0] if len(v) == 1 else v


class Endpoint(BaseEndpoint):
    """Generate synchronous requests and return responses."""

    __slots__ = ("_session",)

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None = None,
        session: requests.Session | None = None,
        timeout: TimeoutType = 60,
        *,
        dry_run: bool = False,
    ) -> None:
        """Initialize a new Endpoint instance for synchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: requests auth tuple or None.
            session: Optional pre-configured requests.Session instance.
            timeout: Base request timeout.
            dry_run: Execution sandbox flag.
        """
        super().__init__(url, headers, auth, timeout=timeout, dry_run=dry_run)
        self._session = session or requests.Session()

    def api_call(  # noqa: PLR0914, PLR0915
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: TimeoutType = None,
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> APIResponseType:  # noqa: PLR0914, PLR0915 - Core request loop contains complex retry/sandbox logic
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
        """
        safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs = (
            self._prepare_request(method, url, domain, timeout, headers, kwargs)
        )

        SecurityGuard.validate_no_control_characters(target_url, context="Endpoint URL")

        # Prepare payload & headers via BaseEndpoint helper
        data, safe_headers = self._prepare_payload(data, files, safe_headers)

        # --- DRY RUN INTERCEPTOR (SYNC) ---
        if self.dry_run:
            logger.info(
                "DRY RUN: Intercepting sync %s request to %s",
                safe_method.upper(),
                safe_url_for_log,
            )
            mock_resp = Response()
            mock_resp.status_code = HTTPStatus.OK
            mock_resp._content = b'{"message": "Dry run successful - request intercepted", "id": "<dry-run-mock-id>"}'  # ruff: ignore[private-member-access]
            mock_resp.encoding = "utf-8"
            mock_resp.url = target_url
            return mock_resp

        req_method = getattr(self._session, safe_method.lower())
        policy = getattr(self, "retry_policy", None) or RetryPolicy()
        max_attempts = policy.max_retries + 1

        sys.audit("mailgun.api.request", safe_method.upper(), safe_url_for_log)
        logger.debug("Sending Request: %s %s", safe_method.upper(), safe_url_for_log)

        response = None

        for attempt in range(max_attempts):
            try:
                response = req_method(
                    target_url,
                    data=data,
                    params=filters,
                    headers=safe_headers,
                    auth=auth,
                    timeout=safe_timeout,
                    files=files,
                    verify=True,
                    stream=False,
                    allow_redirects=False,
                    **safe_kwargs,
                )

                status_code = getattr(response, "status_code", 200)
                is_transient_error = status_code in {429, 500, 502, 503, 504}

                if is_transient_error and attempt < max_attempts - 1:
                    delay = self._compute_retry_delay(policy, status_code, response, attempt)

                    logger.warning(
                        "API Transient Error %s | Retrying in %.2fs (Attempt %d/%d) | URL: %s",
                        status_code,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                        safe_url_for_log,
                    )
                    self._reset_stream_pointers(files)
                    time.sleep(delay)
                    continue

                self._log_response_status(
                    status_code, safe_method, safe_url_for_log, is_async=False
                )
                break

            except requests.RequestException as e:
                # Client-side configuration and validation errors are unrecoverable; do not retry
                if isinstance(
                    e,
                    (
                        requests.exceptions.InvalidURL,
                        requests.exceptions.InvalidHeader,
                        requests.exceptions.InvalidSchema,
                        requests.exceptions.MissingSchema,
                    ),
                ):
                    self._handle_api_error(e, safe_method, target_url)

                if attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)

                    logger.warning(
                        "Network Error: %s | Retrying in %.2fs | URL: %s",
                        e,
                        delay,
                        safe_url_for_log,
                    )

                    self._reset_stream_pointers(files)

                    time.sleep(delay)

                    continue

                if isinstance(e, requests.Timeout):
                    logger.exception(
                        "Request timed out for %s %s",
                        safe_method.upper(),
                        safe_url_for_log,
                    )

                elif isinstance(e, requests.ConnectionError):
                    logger.critical(
                        "Network routing failed for %s %s: %s",
                        safe_method.upper(),
                        safe_url_for_log,
                        e,
                    )

                else:
                    logger.exception(
                        "API request failed for %s %s",
                        safe_method.upper(),
                        safe_url_for_log,
                    )

                self._handle_api_error(e, safe_method, target_url)

        return response

    def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> APIResponseType:
        """Send a GET request to retrieve resources.

        Args:
            filters: Query parameters to include in the request.
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return self.api_call(
            self._auth,
            "get",
            self._url,
            domain=domain,
            headers=merged_headers,
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
    ) -> APIResponseType:
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
        if headers is not None:
            kwargs["headers"] = headers
        merged_headers = self._merge_headers(kwargs)

        return self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def put(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> APIResponseType:
        """Send a PUT request to update or replace a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return self.api_call(
            self._auth,
            "put",
            self._url,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def patch(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> APIResponseType:
        """Send a PATCH request to partially update a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return self.api_call(
            self._auth,
            "patch",
            self._url,
            domain=domain,
            data=data,
            headers=merged_headers,
            filters=filters,
            **kwargs,
        )

    def update(
        self,
        data: Any | None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> APIResponseType:
        """Send a PUT request specifically structured for updating resources with dynamic headers.

        Args:
            data: Payload data (form data or JSON).
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments, including custom 'headers', to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return self.api_call(
            self._auth,
            "put",
            self._url,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def delete(self, domain: str | None = None, **kwargs: Any) -> APIResponseType:
        """Send a DELETE request to remove a resource.

        Args:
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return self.api_call(
            self._auth,
            "delete",
            self._url,
            headers=merged_headers,
            domain=domain,
            **kwargs,
        )

    def stream(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Lazy pagination: yield records one by one without loading all into memory.

        Automatically traverses the 'paging' links returned by the Mailgun API.

        Yields:
            Individual records from the paginated API response.

        Raises:
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        initial_filters = dict(filters) if filters else {}
        current_filters = initial_filters.copy()
        prev_url: str | None = None

        while True:
            # Pass a copy of the dictionary so the mock (and the underlying request layer)
            # receives a frozen snapshot of the state for this specific loop iteration.
            response = self.get(filters=current_filters.copy(), domain=domain, **kwargs)

            if hasattr(response, "raise_for_status"):
                try:
                    response.raise_for_status()
                except requests.HTTPError as exc:
                    raise ApiError(exc.response) from exc

            data = response.json()
            if not isinstance(data, dict):
                break
            items = data.get("items") or []

            # Yield items one by one (Lazy Evaluation)
            yield from items

            paging_dict = data.get("paging") or {}
            next_url = paging_dict.get("next")
            if not next_url or not items or next_url == prev_url:
                break
            prev_url = next_url

            # Mailgun returns a full URL. Parse it to extract just the new pagination parameters
            # (like 'page' or 'url') so the next self.get() call works correctly.
            self._advance_pagination_filters(next_url, initial_filters, current_filters)


# ==============================================================================
# 6. ASYNCHRONOUS IMPLEMENTATION
# ==============================================================================


class AsyncEndpoint(BaseEndpoint):
    """Generate async requests and return responses using httpx2."""

    __slots__ = ("_client",)

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        client: _httpx2_mod.AsyncClient | None = None,
        timeout: TimeoutType = 60,
        *,
        dry_run: bool = False,
    ) -> None:
        """Initialize a new AsyncEndpoint instance for asynchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: httpx auth tuple or None.
            client: Optional httpx2.AsyncClient instance to reuse.
            timeout: Base request timeout.
            dry_run: Execution sandbox flag.

        Raises:
            ImportError: If the optional ``httpx2`` dependency is not installed.
        """
        if httpx2 is None:
            msg = "AsyncEndpoint requires the 'async' extra. Install it with: pip install 'mailgun[async]'"
            raise ImportError(msg)
        super().__init__(url, headers, auth, timeout=timeout, dry_run=dry_run)
        self._client = client or httpx2.AsyncClient()

    async def api_call(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        auth: tuple[str, str] | None,
        method: str,
        url: dict[str, Any],
        headers: dict[str, str],
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        timeout: TimeoutType = None,  # ruff: ignore[async-function-with-timeout]
        files: Any | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> AsyncAPIResponseType:  # noqa: PLR0912, PLR0914, PLR0915
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
        """
        safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs = (
            self._prepare_request(method, url, domain, timeout, headers, kwargs)
        )

        SecurityGuard.validate_no_control_characters(target_url, context="Endpoint URL")

        data, safe_headers = self._prepare_payload(data, files, safe_headers)

        # --- DRY RUN INTERCEPTOR (ASYNC) ---
        if self.dry_run:
            logger.info(
                "DRY RUN: Intercepting async %s request to %s",
                safe_method.upper(),
                safe_url_for_log,
            )
            mock_request = httpx2.Request(safe_method.upper(), target_url)
            return httpx2.Response(
                HTTPStatus.OK,
                request=mock_request,
                content=b'{"message": "Dry run successful - request intercepted", "id": "<dry-run-mock-id>"}',
            )

        if isinstance(safe_timeout, tuple) and len(safe_timeout) == 2:  # noqa: PLR2004
            safe_timeout = httpx2.Timeout(safe_timeout[1], connect=safe_timeout[0])

        request_kwargs: dict[str, Any] = {
            "method": safe_method.upper(),
            "url": target_url,
            "params": filters,
            "headers": safe_headers,
            "auth": auth,
            "timeout": safe_timeout,
            "follow_redirects": False,
        }

        # Safe kwargs passthrough (e.g., allow_redirects)
        request_kwargs.update(safe_kwargs)

        if data is not None:
            if isinstance(data, (str, bytes)):
                request_kwargs["content"] = data
            else:
                request_kwargs["data"] = data

        if files is not None:
            request_kwargs["files"] = files

        policy = getattr(self, "retry_policy", None) or RetryPolicy()
        max_attempts = policy.max_retries + 1

        sys.audit("mailgun.api.request", safe_method.upper(), safe_url_for_log)
        logger.debug("Sending Async Request: %s %s", safe_method.upper(), safe_url_for_log)

        response = None

        for attempt in range(max_attempts):
            try:
                response = await self._client.request(**request_kwargs)

                status_code = getattr(response, "status_code", 200)
                is_transient_error = status_code in {429, 500, 502, 503, 504}

                if is_transient_error and attempt < max_attempts - 1:
                    delay = self._compute_retry_delay(policy, status_code, response, attempt)

                    logger.warning(
                        "API Async Transient Error %s | Retrying in %.2fs (Attempt %d/%d) | URL: %s",
                        status_code,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                        safe_url_for_log,
                    )
                    self._reset_stream_pointers(files)
                    await asyncio.sleep(delay)
                    continue

                self._log_response_status(status_code, safe_method, safe_url_for_log, is_async=True)

                break

            except httpx2.RequestError as e:
                # Protocol and decoding violations are non-transient; do not retry
                if isinstance(e, (httpx2.UnsupportedProtocol, httpx2.DecodingError)):
                    self._handle_api_error(e, safe_method, target_url)

                if attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)

                    logger.warning(
                        "Async Network Error: %s | Retrying in %.2fs (Attempt %d/%d) | URL: %s",
                        e,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                        safe_url_for_log,
                    )

                    self._reset_stream_pointers(files)

                    await asyncio.sleep(delay)

                    continue

                if isinstance(e, httpx2.TimeoutException):
                    logger.exception(
                        "Request timed out for %s %s",
                        safe_method.upper(),
                        safe_url_for_log,
                    )

                elif isinstance(e, (httpx2.ConnectError, httpx2.NetworkError)):
                    logger.critical(
                        "Network routing failed for %s %s: %s",
                        safe_method.upper(),
                        safe_url_for_log,
                        e,
                    )

                else:
                    logger.exception(
                        "API request failed for %s %s",
                        safe_method.upper(),
                        safe_url_for_log,
                    )

                self._handle_api_error(e, safe_method, target_url)

        return response

    async def get(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> AsyncAPIResponseType:
        """Send an asynchronous GET request to retrieve resources.

        Args:
            filters: Query parameters to include in the request.
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return await self.api_call(
            self._auth,
            "get",
            self._url,
            domain=domain,
            headers=merged_headers,
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
    ) -> AsyncAPIResponseType:
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
        if headers is not None:
            kwargs["headers"] = headers
        merged_headers = self._merge_headers(kwargs)

        return await self.api_call(
            self._auth,
            "post",
            self._url,
            files=files,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def put(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> AsyncAPIResponseType:
        """Send an asynchronous PUT request to update or replace a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return await self.api_call(
            self._auth,
            "put",
            self._url,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def patch(
        self,
        data: Any | None = None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> AsyncAPIResponseType:
        """Send an asynchronous PATCH request to partially update a resource.

        Args:
            data: Payload data to include in the request.
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return await self.api_call(
            self._auth,
            "patch",
            self._url,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def update(
        self,
        data: Any | None,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> AsyncAPIResponseType:
        """Send an asynchronous PUT request specifically structured for updating resources with dynamic headers.

        Args:
            data: Payload data (form data or JSON).
            filters: Query parameters to include in the request.
            **kwargs: Additional arguments, including custom 'headers', to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)

        return await self.api_call(
            self._auth,
            "put",
            self._url,
            domain=domain,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def delete(self, domain: str | None = None, **kwargs: Any) -> AsyncAPIResponseType:
        """Send an asynchronous DELETE request to remove a resource.

        Args:
            domain: Target domain name.
            **kwargs: Additional arguments to pass to the HTTP client.

        Returns:
            The HTTP response object.
        """
        merged_headers = self._merge_headers(kwargs)
        return await self.api_call(
            self._auth,
            "delete",
            self._url,
            headers=merged_headers,
            domain=domain,
            **kwargs,
        )

    async def stream(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Lazy pagination: yield records asynchronously one by one without loading all into memory.

        Automatically traverses the 'paging' links returned by the Mailgun API.

        Yields:
            Individual records from the paginated API response.

        Raises:
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        initial_filters = dict(filters) if filters else {}
        current_filters = initial_filters.copy()
        prev_url: str | None = None

        while True:
            response = await self.get(filters=current_filters.copy(), domain=domain, **kwargs)

            # Defensive status check: Convert raw HTTPStatusError into SDK's standard ApiError
            if hasattr(response, "raise_for_status"):
                try:
                    response.raise_for_status()
                except httpx2.HTTPStatusError as exc:
                    raise ApiError(exc.response) from exc

            data = response.json()
            # Stop if response payload is not a valid JSON mapping (e.g. error list or gateway shock)
            if not isinstance(data, dict):
                break

            items = data.get("items") or []
            for item in items:
                yield item

            paging_dict = data.get("paging") or {}
            next_url = paging_dict.get("next")
            if not next_url or not items or next_url == prev_url:
                break
            prev_url = next_url

            # Mailgun returns a full URL. Parse it to extract just the new pagination parameters
            # (like 'page' or 'url') so the next self.get() call works correctly.
            self._advance_pagination_filters(next_url, initial_filters, current_filters)

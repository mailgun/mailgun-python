from __future__ import annotations

import asyncio
import json
import sys
import time
import warnings
from functools import lru_cache
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import parse_qs, urlparse

import requests
from requests.models import Response  # pyright: ignore[reportMissingModuleSource]

from mailgun import routes
from mailgun._httpx_compat import httpx
from mailgun.config import RetryPolicy
from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError
from mailgun.logger import get_logger
from mailgun.security import SecurityGuard


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from mailgun.sandbox import MockResponse
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
    return "".join(f"/{SecurityGuard.sanitize_path_segment(k)}" for k in keys_seq if k)


@lru_cache(maxsize=32)
def _load_handler(endpoint_key: str) -> Callable[..., str]:  # noqa: PLR0911, PLR0912
    """Lazy load the API URL handler for a specific endpoint using SAST-safe literal imports.

    This maintains zero-I/O startup performance. The lru_cache ensures this branching logic
    is executed exactly once per route type.

    Returns:
        Callable: The specific handler function for the requested endpoint.
    """
    # Group 1: Domains Handler (Most common aliases grouped for speed)
    if endpoint_key in {"domains", "dkim_authority", "dkim_selector", "web_prefix"}:
        from mailgun.handlers.domains_handler import handle_domains  # noqa: PLC0415

        return handle_domains
    if endpoint_key == "domainlist":
        from mailgun.handlers.domains_handler import handle_domainlist  # noqa: PLC0415

        return handle_domainlist
    if endpoint_key == "dkim":
        from mailgun.handlers.domains_handler import handle_dkimkeys  # noqa: PLC0415

        return handle_dkimkeys
    if endpoint_key == "sending_queues":
        from mailgun.handlers.domains_handler import handle_sending_queues  # noqa: PLC0415

        return handle_sending_queues
    if endpoint_key == "mailboxes":
        from mailgun.handlers.domains_handler import handle_mailboxes_credentials  # noqa: PLC0415

        return handle_mailboxes_credentials
    if endpoint_key == "webhooks":
        from mailgun.handlers.domains_handler import handle_webhooks  # noqa: PLC0415

        return handle_webhooks

    # Group 2: Suppressions
    if endpoint_key == "bounces":
        from mailgun.handlers.suppressions_handler import handle_bounces  # noqa: PLC0415

        return handle_bounces
    if endpoint_key == "unsubscribes":
        from mailgun.handlers.suppressions_handler import handle_unsubscribes  # noqa: PLC0415

        return handle_unsubscribes
    if endpoint_key == "whitelists":
        from mailgun.handlers.suppressions_handler import handle_whitelists  # noqa: PLC0415

        return handle_whitelists
    if endpoint_key == "complaints":
        from mailgun.handlers.suppressions_handler import handle_complaints  # noqa: PLC0415

        return handle_complaints

    # Group 3: Specific Services
    if endpoint_key == "resendmessage":
        from mailgun.handlers.messages_handler import handle_resend_message  # noqa: PLC0415

        return handle_resend_message
    if endpoint_key == "ips":
        from mailgun.handlers.ips_handler import handle_ips  # noqa: PLC0415

        return handle_ips
    if endpoint_key == "ip_pools":
        from mailgun.handlers.ip_pools_handler import handle_ippools  # noqa: PLC0415

        return handle_ippools
    if endpoint_key == "tags":
        from mailgun.handlers.tags_handler import handle_tags  # noqa: PLC0415

        return handle_tags
    if endpoint_key == "routes":
        from mailgun.handlers.routes_handler import handle_routes  # noqa: PLC0415

        return handle_routes
    if endpoint_key == "lists":
        from mailgun.handlers.mailinglists_handler import handle_lists  # noqa: PLC0415

        return handle_lists
    if endpoint_key == "templates":
        from mailgun.handlers.templates_handler import handle_templates  # noqa: PLC0415

        return handle_templates
    if endpoint_key == "addressvalidate":
        from mailgun.handlers import email_validation_handler as evh  # noqa: PLC0415

        return evh.handle_address_validate
    if endpoint_key == "inbox":
        from mailgun.handlers.inbox_placement_handler import handle_inbox  # noqa: PLC0415

        return handle_inbox
    if endpoint_key == "analytics":
        from mailgun.handlers.metrics_handler import handle_metrics  # noqa: PLC0415

        return handle_metrics
    if endpoint_key == "bounce-classification":
        from mailgun.handlers import bounce_classification_handler as bch  # noqa: PLC0415

        return bch.handle_bounce_classification
    if endpoint_key == "users":
        from mailgun.handlers.users_handler import handle_users  # noqa: PLC0415

        return handle_users
    if endpoint_key == "keys":
        from mailgun.handlers.keys_handler import handle_keys  # noqa: PLC0415

        return handle_keys

    # Group 4: Fallback for "messages", "messages.mime", "events", and unknown routes
    from mailgun.handlers.default_handler import handle_default  # noqa: PLC0415

    return handle_default


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
        self.retry_policy = None

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

        return req_headers

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
            url, domain=target_domain_normalized, method=safe_method, **kwargs
        )
        self._warn_if_deprecated(safe_method, target_url)

        # PEP 578 and protection against Log Forging (CWE-117)
        safe_url_for_log = SecurityGuard.sanitize_log_trace(target_url)

        return safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs


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

        Raises:
            MailgunTimeoutError: If the request times out.
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs = (
            self._prepare_request(method, url, domain, timeout, headers, kwargs)
        )

        SecurityGuard.validate_no_control_characters(target_url, context="Endpoint URL")

        # --- DRY RUN INTERCEPTOR (Zero-Leak Sandbox Mode) ---
        if self.dry_run:
            # Route 1: Rich Sandbox Preview for emails
            if "messages" in url.get("keys", []):
                from mailgun.sandbox import LocalSandbox  # noqa: PLC0415

                sandbox_domain = domain or kwargs.get("domain", "local.sandbox")
                payload = data or {}

                logger.info("DRY RUN: Intercepting email payload for local sandbox preview.")
                sandbox = LocalSandbox()
                return sandbox.intercept_and_preview(sandbox_domain, payload)

            # Route 2: Standard JSON Mock for all other endpoints (domains, ips, etc.)
            logger.info(
                "DRY RUN: Intercepting %s request to %s", safe_method.upper(), safe_url_for_log
            )
            mock_resp = Response()
            mock_resp.status_code = HTTPStatus.OK
            mock_resp.encoding = "utf-8"
            mock_resp._content = b'{"message": "Dry run successful - request intercepted", "id": "<dry-run-mock-id>"}'  # noqa: SLF001 - Mocking internal state
            return mock_resp

        # Case-insensitive validation for Content-Type to conform with RFC 7230
        is_json_request = any(
            k.lower() == "content-type" and "application/json" in str(v).lower()
            for k, v in safe_headers.items()
        )

        if is_json_request and data is not None and not isinstance(data, (str, bytes)):
            data = json.dumps(data, separators=(",", ":"))

        req_method = getattr(self._session, safe_method.lower())

        policy = getattr(self, "retry_policy", None) or RetryPolicy()
        max_attempts = policy.max_retries + 1

        sys.audit("mailgun.api.request", safe_method.upper(), safe_url_for_log)
        logger.debug("Sending Request: %s %s", safe_method.upper(), safe_url_for_log)

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

                # Логіка Retry Policy
                if is_transient_error and attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)

                    if status_code == HTTPStatus.TOO_MANY_REQUESTS and policy.respect_retry_after:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)

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

                # Фінальна обробка після виходу з циклу ретраїв
                is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD
                if is_error:
                    logger.error(
                        "API Error %s | %s %s", status_code, safe_method.upper(), safe_url_for_log
                    )
                else:
                    logger.debug(
                        "API Success %s | %s %s", status_code, safe_method.upper(), target_url
                    )

            except requests.RequestException as e:
                if attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)

                    logger.warning(
                        "Network Error: %s | Retrying in %.2fs (Attempt %d/%d) | URL: %s",
                        e,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                        safe_url_for_log,
                    )

                    self._reset_stream_pointers(files)

                    time.sleep(delay)

                    continue

                if isinstance(e, requests.exceptions.Timeout):
                    logger.exception("Timeout Error: %s %s", safe_method.upper(), safe_url_for_log)
                    raise MailgunTimeoutError("Request timed out") from e

                logger.critical(
                    "Connection Failed (DNS/Network): %s | URL: %s", e, safe_url_for_log
                )
                msg = f"Network routing failed: {e}"
                raise ApiError(msg) from e
            return response

        return None

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
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
    ) -> APIResponseType:
        """Send a PUT request to update or replace a resource.

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
            "put",
            self._url,
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    def patch(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
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
            data=data,
            headers=merged_headers,
            filters=filters,
            **kwargs,
        )

    def update(
        self, data: Any | None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
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
            self._auth, "delete", self._url, headers=merged_headers, domain=domain, **kwargs
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
        """
        current_filters = dict(filters) if filters else {}

        while True:
            # Pass a copy of the dictionary so the mock (and the underlying request layer)
            # receives a frozen snapshot of the state for this specific loop iteration.
            response = self.get(filters=current_filters.copy(), domain=domain, **kwargs)

            if hasattr(response, "raise_for_status"):
                response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            # Yield items one by one (Lazy Evaluation)
            yield from items

            # Check for the next page cursor
            next_url = data.get("paging", {}).get("next")

            # Stop if there's no next URL or the current page was empty
            if not next_url or not items:
                break

            # Mailgun returns a full URL. Parse it to extract just the new pagination parameters
            # (like 'page' or 'url') so the next self.get() call works correctly.
            query_params = parse_qs(urlparse(next_url).query)
            current_filters.update({k: v[0] for k, v in query_params.items()})


# ==============================================================================
# 6. ASYNCHRONOUS IMPLEMENTATION
# ==============================================================================


class AsyncEndpoint(BaseEndpoint):
    """Generate async requests and return responses using httpx."""

    __slots__ = ("_client",)

    def __init__(
        self,
        url: dict[str, Any],
        headers: dict[str, str],
        auth: tuple[str, str] | None,
        client: httpx.AsyncClient | None = None,
        timeout: TimeoutType = 60,
        *,
        dry_run: bool = False,
    ) -> None:
        """Initialize a new AsyncEndpoint instance for asynchronous API interaction.

        Args:
            url: URL dictionary with pairs {"base": "keys"}.
            headers: Headers dictionary.
            auth: httpx auth tuple or None.
            client: Optional httpx.AsyncClient instance to reuse.
            timeout: Base request timeout.
            dry_run: Execution sandbox flag.
        """
        super().__init__(url, headers, auth, timeout=timeout, dry_run=dry_run)
        self._client = client or httpx.AsyncClient()

    async def api_call(  # noqa: PLR0914, PLR0915
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
    ) -> Response | MockResponse | None:  # noqa: PLR0914, PLR0915
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
            MailgunTimeoutError: If the request times out.
            ApiError: If the server returns a 4xx or 5xx status code or a network error occurs.
        """
        safe_method, target_url, safe_url_for_log, safe_timeout, safe_headers, safe_kwargs = (
            self._prepare_request(method, url, domain, timeout, headers, kwargs)
        )

        SecurityGuard.validate_no_control_characters(target_url, context="Endpoint URL")

        # --- DRY RUN INTERCEPTOR (ASYNC) ---
        if self.dry_run:
            if "messages" in url.get("keys", []):
                from mailgun.sandbox import LocalSandbox  # noqa: PLC0415

                sandbox_domain = domain or kwargs.get("domain", "local.sandbox")
                payload = data or {}

                logger.info("DRY RUN: Intercepting async email payload for local sandbox preview.")
                sandbox = LocalSandbox()
                return sandbox.intercept_and_preview(sandbox_domain, payload)

            logger.info(
                "DRY RUN: Intercepting async %s request to %s",
                safe_method.upper(),
                safe_url_for_log,
            )
            return httpx.Response(
                status_code=200,
                json={
                    "message": "Dry run successful - request intercepted",
                    "id": "<dry-run-mock-id>",
                },
                request=httpx.Request(method=safe_method.upper(), url=target_url),
            )

        if isinstance(safe_timeout, tuple):
            safe_timeout = httpx.Timeout(safe_timeout[1], connect=safe_timeout[0])

        # Case-insensitive validation for Content-Type to conform with RFC 7230
        is_json_request = any(
            k.lower() == "content-type" and "application/json" in str(v).lower()
            for k, v in safe_headers.items()
        )

        if is_json_request and data is not None and not isinstance(data, (str, bytes)):
            data = json.dumps(data, separators=(",", ":"))

        request_kwargs: dict[str, Any] = {
            "method": safe_method.upper(),
            "url": target_url,
            "params": filters,
            "files": files,
            "headers": safe_headers,
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

        policy = getattr(self, "retry_policy", None) or RetryPolicy()
        max_attempts = policy.max_retries + 1

        # PEP 578 and protection against Log Forging (CWE-117)
        sys.audit("mailgun.api.request", safe_method.upper(), safe_url_for_log)
        logger.debug("Sending Async Request: %s %s", safe_method.upper(), safe_url_for_log)

        for attempt in range(max_attempts):
            try:
                response = await self._client.request(**request_kwargs)

                status_code = getattr(response, "status_code", 200)
                is_transient_error = status_code in {429, 500, 502, 503, 504}

                if is_transient_error and attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)

                    if status_code == HTTPStatus.TOO_MANY_REQUESTS and policy.respect_retry_after:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)

                    logger.warning(
                        "API Transient Error %s | Async Retrying in %.2fs (Attempt %d/%d)",
                        status_code,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                    )
                    self._reset_stream_pointers(files)
                    await asyncio.sleep(delay)
                    continue

                is_error = isinstance(status_code, int) and status_code >= _HTTP_ERROR_THRESHOLD
                if is_error:
                    logger.error(
                        "API Error %s | %s %s", status_code, safe_method.upper(), safe_url_for_log
                    )
                else:
                    logger.debug(
                        "API Success %s | %s %s", status_code, safe_method.upper(), target_url
                    )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
                if attempt < max_attempts - 1:
                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        "Async Network Error: %s | Retrying in %.2fs (Attempt %d/%d)",
                        e,
                        delay,
                        attempt + 1,
                        policy.max_retries,
                    )
                    self._reset_stream_pointers(files)
                    await asyncio.sleep(delay)
                    continue

                if isinstance(e, httpx.TimeoutException):
                    logger.exception("Timeout Error: %s %s", safe_method.upper(), safe_url_for_log)
                    raise MailgunTimeoutError("Request timed out") from e

                logger.critical("Async Connection Failed: %s | URL: %s", e, safe_url_for_log)
                msg = f"Network routing failed: {e}"
                raise ApiError(msg) from e

            return response

        return None

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
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
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
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def patch(
        self, data: Any | None = None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
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
            headers=merged_headers,
            data=data,
            filters=filters,
            **kwargs,
        )

    async def update(
        self, data: Any | None, filters: Mapping[str, str | Any] | None = None, **kwargs: Any
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
            self._auth, "delete", self._url, headers=merged_headers, domain=domain, **kwargs
        )

    async def stream(
        self,
        filters: Mapping[str, str | Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Lazy pagination: yield records asynchronously one by one.

        Yields:
            Individual records from the paginated API response.
        """
        current_filters = dict(filters) if filters else {}

        while True:
            response = await self.get(filters=current_filters.copy(), domain=domain, **kwargs)

            if hasattr(response, "raise_for_status"):
                response.raise_for_status()

            data = response.json()
            items = data.get("items", [])
            for item in items:
                yield item

            next_url = data.get("paging", {}).get("next")
            if not next_url or not items:
                break

            query_params = parse_qs(urlparse(next_url).query)
            current_filters.update({k: v[0] for k, v in query_params.items()})

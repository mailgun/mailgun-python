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

import contextlib
import ssl
import warnings
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Self

import requests  # pyright: ignore[reportMissingModuleSource]

from mailgun._httpx_compat import httpx
from mailgun.config import Config
from mailgun.endpoints import AsyncEndpoint, BaseEndpoint, Endpoint
from mailgun.filters import RedactingFilter
from mailgun.security import SecretAuth, SecureHTTPAdapter, SecurityGuard


if TYPE_CHECKING:
    import types

# ==============================================================================
# 1. PUBLIC API & GLOBALS
# ==============================================================================

__all__ = [
    "AsyncClient",
    "AsyncEndpoint",
    "BaseClient",
    "BaseEndpoint",
    "Client",
    "Config",
    "Endpoint",
    "RedactingFilter",
    "SecretAuth",
    "SecureHTTPAdapter",
    "SecurityGuard",
]


# Constants for API error handling and logging (fixes Ruff PLR2004)
_MAX_LOG_LENGTH: Final[int] = 500
_AUTH_TUPLE_LEN: Final = 2
_TIMEOUT_TUPLE_LEN: Final[int] = 2
_DEFAULT_TIMEOUT = 60.0


# ==============================================================================
# 1. BASE CLASS (Abstract Interface)
# ==============================================================================


class BaseClient:
    """Base class for API clients that holds common state and initialization logic."""

    __slots__ = ("auth", "config", "timeout")

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
        self.config = Config(
            api_url=kwargs.get("api_url"),
            dry_run=kwargs.get("dry_run", False),
            retry_policy=kwargs.get("retry_policy"),
        )

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
        self.timeout = kwargs.get("timeout", _DEFAULT_TIMEOUT)

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
        return sorted(set(super().__dir__()) | self.config.available_endpoints)


# ==============================================================================
# 2. SYNCHRONOUS IMPLEMENTATION
# ==============================================================================


class Client(BaseClient):
    """Synchronous client class."""

    __slots__ = ("_session",)

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

        adapter = SecureHTTPAdapter(pool_connections=100, pool_maxsize=100)
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
            endpoint = Endpoint(
                url=url,
                headers=headers,
                auth=self.auth,
                session=self._session,
                timeout=self.timeout,
                dry_run=self.config.dry_run,
            )

        except KeyError:
            # __getattr__ must return AttributeError
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from None

        endpoint.retry_policy = getattr(self.config, "retry_policy", None)
        return endpoint

    def close(self) -> None:
        """Close the underlying requests.Session connection pool and purge memory."""
        # Safely fetch without triggering AttributeError on unbound slots
        session = getattr(self, "_session", None)
        if session:
            try:
                # CWE-316: Clear session resources
                session.auth = None
                session.headers.clear()
                session.close()
            finally:
                self._session = None
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

    def __del__(self) -> None:
        """Emit a ResourceWarning if the client is garbage-collected without being closed."""
        if getattr(self, "_session", None) is not None:
            warnings.warn(
                "Unclosed Client detected. Please use the client as a context manager or call client.close() explicitly.",
                ResourceWarning,
                stacklevel=2,
            )
            with contextlib.suppress(Exception):
                self.close()

    def ping(self) -> bool:
        """Perform a fast, low-overhead health check to verify API credentials.

        This checks network connectivity to the Mailgun infrastructure.
        This method is fail-safe: it will never raise network exceptions or
        authentication errors to the application layer. Instead, it returns a
        clean boolean value, making it ideal for container readiness probes.

        Returns:
            bool: True if the connection succeeds and credentials are valid (HTTP 200),
                  False on network timeouts, DNS drops, or invalid API keys.
        """
        try:
            # Query the domains endpoint with a strict limit of 1
            response = self.domains.get(filters={"limit": 1})
        except Exception:  # noqa: BLE001 - Explicitly failing closed on readiness probe
            return False
        else:
            if hasattr(response, "status_code"):
                return bool(response.status_code == HTTPStatus.OK)
            return False


# ==============================================================================
# 2. ASYNC IMPLEMENTATION
# ==============================================================================


class AsyncClient(BaseClient):
    """Async client class using httpx."""

    __slots__ = ("_client_kwargs", "_httpx_client")

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

            endpoint = AsyncEndpoint(
                url=url,
                headers=headers,
                auth=self.auth,
                client=self._client,
                timeout=self.timeout,
                dry_run=self.config.dry_run,
            )

        except KeyError:
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg) from None

        endpoint.retry_policy = getattr(self.config, "retry_policy", None)
        return endpoint

    @property
    def _client(self) -> httpx.AsyncClient:
        """Provide lazy initialization for the underlying httpx.AsyncClient.

        Returns:
            The active httpx.AsyncClient instance.
        """
        # Assign to a local variable so Pyright can properly narrow the type
        current_client: httpx.AsyncClient | None = getattr(self, "_httpx_client", None)

        if current_client is None or current_client.is_closed:
            # Enforce TLS 1.2+ for httpx (CWE-319)
            ssl_context = ssl.create_default_context()
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Check if the user already provided a custom transport (e.g. for mocking)
            kwargs = self._client_kwargs.copy()
            if "transport" not in kwargs:
                limits = httpx.Limits(max_keepalive_connections=100, max_connections=100)
                kwargs["transport"] = httpx.AsyncHTTPTransport(
                    retries=3, limits=limits, verify=ssl_context
                )

            self._httpx_client = httpx.AsyncClient(**kwargs)
            return self._httpx_client

        return current_client

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient and purge memory."""
        if self._httpx_client:
            try:
                # CWE-316: Clear async session
                self._httpx_client.auth = None
                self._httpx_client.headers.clear()
                await self._httpx_client.aclose()
            finally:
                self._httpx_client = None
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

    def __del__(self) -> None:
        """Safety net for unclosed sockets (CWE-400) if context managers are skipped."""
        if self._httpx_client is not None and not self._httpx_client.is_closed:
            warnings.warn(
                f"Unclosed {self.__class__.__name__} detected. You must explicitly "
                "call '.aclose()' or use the 'async with' context manager to prevent "
                "socket and memory leaks.",
                ResourceWarning,
                stacklevel=2,
            )

    async def ping(self) -> bool:
        """Perform a fast, low-overhead health check to verify API credentials.

        This checks network connectivity to the Mailgun infrastructure.
        This method is fail-safe: it will never raise network exceptions or
        authentication errors to the application layer. Instead, it returns a
        clean boolean value, making it ideal for container readiness probes.

        Returns:
            bool: True if the connection succeeds and credentials are valid (HTTP 200),
                  False on network timeouts, DNS drops, or invalid API keys.
        """
        try:
            # Query the domains endpoint with a strict limit of 1
            response = await self.domains.get(filters={"limit": 1})
        except Exception:  # noqa: BLE001 - Explicitly failing closed on readiness probe
            return False
        else:
            if hasattr(response, "status_code"):
                return bool(response.status_code == HTTPStatus.OK)
            return False

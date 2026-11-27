"""In-memory test doubles for Mailgun SDK downstream unit testing."""

from __future__ import annotations

from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, Self, cast

from mailgun.handlers.error_handler import ApiError


if TYPE_CHECKING:
    from types import TracebackType

    from mailgun.types import TimeoutType


__all__ = ["MockEndpoint", "MockMailgunClient", "MockResponse"]

_HTTP_ERROR_THRESHOLD: Final[int] = 400


class _ResolvedAwaitable:
    """Zero-overhead iterator completing ``await`` immediately with a precomputed value."""

    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        self._value = value

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Any:
        raise StopIteration(self._value)


@dataclass(slots=True)
class MockResponse:
    """In-memory response object mimicking ``requests.Response`` and ``httpx2.Response``."""

    status_code: int = 200
    _payload: dict[str, Any] = field(
        default_factory=lambda: {
            "id": "<mock-mailgun-id>",
            "message": "Queued. Thank you.",
            "items": [],
        },
    )
    headers: dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"},
    )
    url: str = "https://api.mailgun.net/v3/mock"
    text: str = ""

    def json(self) -> dict[str, Any]:
        """Return a shallow copy of the synthetic JSON payload.

        Returns:
            dict[str, Any]: Synthetic Mailgun API response body.
        """
        return dict(self._payload)

    def raise_for_status(self) -> None:
        """Raise :class:`ApiError` when ``status_code >= 400``.

        Raises:
            ApiError: If the mock response represents an HTTP error status.
        """
        if self.status_code >= _HTTP_ERROR_THRESHOLD:
            msg = f"Mock HTTP {self.status_code} error for {self.url}"
            raise ApiError(msg)

    def __await__(self) -> Generator[Any, None, Self]:
        """Allow ``MockResponse`` instances to be ``await``ed transparently in async tests.

        Returns:
            Generator[Any, None, Self]: Awaitable iterator resolving to ``self``.
        """
        return cast("Generator[Any, None, Self]", _ResolvedAwaitable(self))


class _MockStreamIterator:
    """Dual sync/async iterator yielded by :meth:`MockEndpoint.stream`."""

    __slots__ = ("_index", "_items")

    def __init__(self, items: tuple[dict[str, Any], ...] = ()) -> None:
        self._items = items
        self._index = 0

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> dict[str, Any]:
        if self._index >= len(self._items):
            raise StopIteration
        item = self._items[self._index]
        self._index += 1
        return item

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> dict[str, Any]:
        try:
            return next(self)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _MockPingResult:
    """Boolean-like ping probe result supporting both sync truth checks and ``await``."""

    __slots__ = ("_ok",)

    def __init__(self, *, ok: bool) -> None:
        self._ok = ok

    def __bool__(self) -> bool:
        return self._ok

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (bool, _MockPingResult)):
            return self._ok is bool(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._ok)

    def __repr__(self) -> str:
        return repr(self._ok)

    def __await__(self) -> Generator[Any, None, bool]:
        return cast("Generator[Any, None, bool]", _ResolvedAwaitable(self._ok))


@dataclass(slots=True)
class MockEndpoint:
    """Recorded endpoint proxy returned by dynamic attribute access on :class:`MockMailgunClient`."""

    client: MockMailgunClient
    name: str

    def _next_response(self, method: str) -> MockResponse:
        if self.client.queued_responses:
            return self.client.queued_responses.pop(0)

        route_responses = self.client.route_responses
        if (self.name, method) in route_responses:
            return route_responses[self.name, method]
        if self.name in route_responses:
            return route_responses[self.name]

        status = self.client.default_status
        return MockResponse(
            status_code=status,
            _payload={
                "id": "<mock-mailgun-id>",
                "message": "Queued. Thank you." if status < _HTTP_ERROR_THRESHOLD else "Mock error",
                "items": [],
            },
            url=f"https://api.mailgun.net/v3/{self.name}",
        )

    def _record(
        self,
        method: str,
        *,
        domain: str | None = None,
        data: Any | None = None,
        filters: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        files: Any | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        extra_kwargs = dict(kwargs)
        resolved_headers = headers
        if resolved_headers is None and isinstance(extra_kwargs.get("headers"), Mapping):
            resolved_headers = extra_kwargs.pop("headers")

        recorded_data = dict(data) if isinstance(data, Mapping) and type(data) is not dict else data
        record: dict[str, Any] = {
            "endpoint": self.name,
            "method": method,
            "domain": domain,
            "data": recorded_data,
            "filters": dict(filters) if filters is not None else None,
            "headers": dict(resolved_headers) if resolved_headers is not None else None,
            "files": files,
            "kwargs": extra_kwargs,
        }
        self.client.sent_requests.append(record)
        return self._next_response(method)

    def get(
        self,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        """Record a mock GET request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record("GET", domain=domain, filters=filters, **kwargs)

    def create(
        self,
        data: Any | None = None,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        headers: Mapping[str, str] | None = None,
        files: Any | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        """Record a mock POST request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record(
            "POST",
            domain=domain,
            data=data,
            filters=filters,
            headers=headers,
            files=files,
            **kwargs,
        )

    def put(
        self,
        data: Any | None = None,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        """Record a mock PUT request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record("PUT", domain=domain, data=data, filters=filters, **kwargs)

    def patch(
        self,
        data: Any | None = None,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        """Record a mock PATCH request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record("PATCH", domain=domain, data=data, filters=filters, **kwargs)

    def update(
        self,
        data: Any | None = None,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> MockResponse:
        """Record a mock PUT update request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record("PUT", domain=domain, data=data, filters=filters, **kwargs)

    def delete(self, domain: str | None = None, **kwargs: Any) -> MockResponse:
        """Record a mock DELETE request and return a synthetic response.

        Returns:
            MockResponse: In-memory mock HTTP response.
        """
        return self._record("DELETE", domain=domain, **kwargs)

    def stream(
        self,
        filters: Mapping[str, Any] | None = None,
        domain: str | None = None,
        **kwargs: Any,
    ) -> _MockStreamIterator:
        """Record a paginated stream request and return a dual sync/async iterator.

        Returns:
            _MockStreamIterator: Iterator supporting both ``for`` and ``async for``.
        """
        response = self._record("GET", domain=domain, filters=filters, **kwargs)
        payload = response.json()
        raw_items = payload.get("items") or []
        items = tuple(dict(item) for item in raw_items if isinstance(item, Mapping))
        return _MockStreamIterator(items)


@dataclass(slots=True)
class MockMailgunClient:
    """Drop-in in-memory Mailgun test double recording sent requests."""

    sent_requests: list[dict[str, Any]] = field(default_factory=list)
    default_status: int = 200
    queued_responses: list[MockResponse] = field(default_factory=list)
    route_responses: dict[str | tuple[str, str], MockResponse] = field(default_factory=dict)

    def enqueue_response(
        self,
        response: MockResponse | None = None,
        *,
        status_code: int = 200,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        url: str = "https://api.mailgun.net/v3/mock",
        text: str = "",
    ) -> MockResponse:
        """Append a synthetic response to :attr:`queued_responses`.

        Returns:
            MockResponse: The queued mock response instance.
        """
        queued = response or MockResponse(
            status_code=status_code,
            _payload=(
                dict(payload)
                if payload is not None
                else {
                    "id": "<mock-mailgun-id>",
                    "message": "Queued. Thank you.",
                    "items": [],
                }
            ),
            headers=(
                dict(headers) if headers is not None else {"Content-Type": "application/json"}
            ),
            url=url,
            text=text,
        )
        self.queued_responses.append(queued)
        return queued

    def __getattr__(self, name: str) -> MockEndpoint:
        """Resolve an arbitrary Mailgun endpoint proxy without network I/O.

        Returns:
            MockEndpoint: Recorded endpoint test double bound to this client.

        Raises:
            AttributeError: If ``name`` is a private or dunder attribute.
        """
        if name.startswith("_"):
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg)
        return MockEndpoint(client=self, name=name)

    def ping(self, timeout: TimeoutType = None) -> _MockPingResult:
        """Return synthetic reachability status usable synchronously or via ``await``.

        Returns:
            _MockPingResult: Truthy when ``default_status < 400``, awaitable to ``bool``.
        """
        _ = timeout
        return _MockPingResult(ok=self.default_status < _HTTP_ERROR_THRESHOLD)

    def close(self) -> None:
        """Close the mock client cleanly (no-op)."""

    async def aclose(self) -> None:
        """Asynchronously close the mock client cleanly (no-op)."""

    def __enter__(self) -> Self:
        """Enter the synchronous context manager.

        Returns:
            Self: The active mock client instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the synchronous context manager."""
        _ = (exc_type, exc_val, exc_tb)
        self.close()

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager.

        Returns:
            Self: The active mock client instance.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the asynchronous context manager."""
        _ = (exc_type, exc_val, exc_tb)
        await self.aclose()

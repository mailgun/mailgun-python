#!/usr/bin/env python3
"""Stateful Hypothesis fuzzer for the Mailgun AsyncClient.

Focus: Complex sequence-based state transitions (Create -> Read -> Update -> Delete),
cursor streaming, post-aclose() safety, and transport resource leak assertions.
"""

import asyncio
from typing import Any

import hypothesis.strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

from mailgun.client import AsyncClient
from mailgun.handlers.error_handler import ApiError
from tests.fuzz.strategies import evil_payloads, get_fuzz_payloads


class MailgunAsyncStateMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client: AsyncClient | None = None
        self.is_open: bool = False
        self.created_domains: set[str] = set()

    @initialize()  # type: ignore[untyped-decorator]
    def setup_client(self) -> None:
        self.client = AsyncClient(auth=("api", "fuzz-key-stateful-12345"))
        self.is_open = True
        self.created_domains.clear()

    @rule(  # type: ignore[untyped-decorator]
        endpoint=st.sampled_from(["domains", "bounces", "complaints", "unsubscribes", "webhooks"]),
        domain=evil_payloads(),  # pyright: ignore[reportCallIssue]
    )
    def call_endpoint_get(self, endpoint: str, domain: str) -> None:
        """Invokes GET / list operations on active endpoints."""
        if not self.is_open or self.client is None:
            return

        ep = getattr(self.client, endpoint, None)
        if ep is None:
            return

        try:
            if hasattr(ep, "get"):
                self.loop.run_until_complete(ep.get(domain=domain))
            elif hasattr(ep, "list"):
                self.loop.run_until_complete(ep.list(domain=domain))
        except (ApiError, ValueError, TypeError, KeyError):
            pass

    @rule(  # type: ignore[untyped-decorator]
        endpoint=st.sampled_from(["messages", "domains", "webhooks"]),
        domain=evil_payloads(),  # pyright: ignore[reportCallIssue]
        data=get_fuzz_payloads(),  # pyright: ignore[reportCallIssue]
    )
    def call_endpoint_post(
        self, endpoint: str, domain: str, data: dict[str, Any]
    ) -> None:
        """Invokes POST / create operations with structured payload trees."""
        if not self.is_open or self.client is None:
            return

        ep = getattr(self.client, endpoint, None)
        if ep is None:
            return

        try:
            if hasattr(ep, "create"):
                self.loop.run_until_complete(ep.create(domain=domain, data=data))
            elif hasattr(ep, "post"):
                self.loop.run_until_complete(ep.post(domain=domain, data=data))

            if endpoint == "domains":
                self.created_domains.add(domain)

        except (ApiError, ValueError, TypeError, KeyError):
            pass

    @rule(domain=evil_payloads())  # type: ignore[untyped-decorator] # pyright: ignore[reportCallIssue]
    def call_endpoint_delete(self, domain: str) -> None:
        """Tests resource deletion and subsequent state transition."""
        if not self.is_open or self.client is None:
            return

        try:
            self.loop.run_until_complete(self.client.domains.delete(domain=domain))
            self.created_domains.discard(domain)
        except (ApiError, ValueError, TypeError, KeyError, AttributeError):
            pass

    @rule(  # type: ignore[untyped-decorator]
        endpoint=st.sampled_from(["bounces", "unsubscribes"]),
        domain=evil_payloads(),  # pyright: ignore[reportCallIssue]
    )
    def call_stream_pagination(self, endpoint: str, domain: str) -> None:
        """Tests streaming cursor consumption with early termination."""
        if not self.is_open or self.client is None:
            return

        ep = getattr(self.client, endpoint, None)
        if ep is None or not hasattr(ep, "stream"):
            return

        async def _consume_stream() -> None:
            count = 0
            async for _ in ep.stream(domain=domain, filters={"limit": 5}):
                count += 1
                if count >= 2:
                    break

        try:
            self.loop.run_until_complete(_consume_stream())
        except (ApiError, ValueError, TypeError, KeyError, StopIteration):
            pass

    @invariant()  # type: ignore[untyped-decorator]
    def check_client_integrity(self) -> None:
        """Asserts client invariants: prevents memory leaks and unhandled closed states."""
        if not self.is_open:
            if self.client is not None and hasattr(self.client, "_httpx_client"):
                assert (
                    self.client._httpx_client is None
                ), "Resource Leak: httpx client persists after aclose()"
        else:
            assert self.client is not None

    @rule()  # type: ignore[untyped-decorator]
    def close_client(self) -> None:
        """Explicit client teardown rule."""
        if self.is_open and self.client is not None:
            self.loop.run_until_complete(self.client.aclose())
            self.is_open = False

    def teardown(self) -> None:
        """Cleanup after test sequence."""
        if self.is_open and self.client is not None:
            self.loop.run_until_complete(self.client.aclose())
            self.is_open = False
        self.loop.close()


TestAsyncClientState = MailgunAsyncStateMachine.TestCase

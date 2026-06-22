#!/usr/bin/env python3
"""Stateful Hypothesis fuzzer for the AsyncClient."""

import asyncio
from typing import Any

import hypothesis.strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from mailgun.client import AsyncClient
from tests.fuzz.strategies import evil_payloads, get_fuzz_payloads


class MailgunAsyncStateMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.client: AsyncClient | None = None
        self.is_open: bool = False
        self.auth: tuple[str, str] = ("api", "fuzz-key")

    @initialize()  # type: ignore[untyped-decorator]
    def setup_client(self) -> None:
        self.client = AsyncClient(auth=self.auth)
        self.is_open = True

    @rule(
        endpoint=st.sampled_from(["bounces", "domains", "messages", "webhooks"]),
        payload=evil_payloads(),  # pyright: ignore[reportCallIssue]
    )  # type: ignore[untyped-decorator]
    def call_endpoint_get(self, endpoint: str, payload: str) -> None:
        """Exercise GET endpoints with randomized 'evil' payloads."""
        if not self.is_open or self.client is None:
            return

        ep = getattr(self.client, endpoint)
        try:
            # Inject payload into domain/id parameters to test path sanitization
            ep.get(domain=payload)
        except Exception:  # noqa: BLE001
            pass

    @rule(
        endpoint=st.sampled_from(["bounces", "domains", "messages", "webhooks"]),
        domain=evil_payloads(),  # pyright: ignore[reportCallIssue]
        data=get_fuzz_payloads(),
    )  # type: ignore[untyped-decorator]
    def call_endpoint_post(
        self, endpoint: str, domain: str, data: dict[str, Any]
    ) -> None:
        """Exercise POST endpoints with complex dictionary payloads."""
        if not self.is_open or self.client is None:
            return

        ep = getattr(self.client, endpoint)
        try:
            # Inject complex dictionary payloads to test internal serialization
            ep.post(domain=domain, data=data)
        except Exception:  # noqa: BLE001
            pass

    @invariant()  # type: ignore[untyped-decorator]
    def check_client_integrity(self) -> None:
        """Oracle assertion: Ensure no resource leaks."""
        if not self.is_open:
            # If the client is closed, ensure the transport is purged
            if self.client is not None and hasattr(self.client, "_httpx_client"):
                assert (
                    self.client._httpx_client is None
                ), "Resource Leak: httpx client persists after aclose()"
        else:
            assert self.client is not None

    @rule()  # type: ignore[untyped-decorator]
    def close_client(self) -> None:
        """Teardown operation."""
        if self.is_open and self.client is not None:
            asyncio.run(self.client.aclose())
            self.is_open = False


TestAsyncClientState = MailgunAsyncStateMachine.TestCase

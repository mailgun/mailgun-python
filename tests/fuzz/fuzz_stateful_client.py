#!/usr/bin/env python3
"""Stateful Fuzzer for the Mailgun Sync Client.

Exercises state transitions, chaos HTTP responses (429/500/503), streaming
pagination shocks, file pointer resets, and post-close lifecycle invariants.
"""

import io
import logging
import socket
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import atheris
import requests

with atheris.instrument_imports():
    from mailgun.client import Client, Config
    from mailgun.config import RetryPolicy
    from mailgun.endpoints import Endpoint
    from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError
    from mailgun.security import IdempotencyGuard, SecurityGuard, SpamGuard

logging.disable(logging.CRITICAL)


class ChaosMockAdapter(requests.adapters.HTTPAdapter):
    """Dynamic HTTP adapter injecting chaotic status codes and payloads."""

    def __init__(self, fdp: atheris.FuzzedDataProvider) -> None:
        super().__init__()
        self.fdp = fdp

    def send(  # type: ignore[override]
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: Any = None,
        verify: Any = True,
        cert: Any = None,
        proxies: Any = None,
    ) -> requests.Response:
        resp = requests.Response()
        resp.request = request

        # Inject chaos responses based on fuzzer state
        status_code = self.fdp.PickValueInList([200, 400, 429, 500, 502, 503])
        resp.status_code = status_code

        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if status_code == 429:
            headers["Retry-After"] = "0"
        resp.headers = requests.structures.CaseInsensitiveDict(headers)

        if status_code == 200:
            resp._content = b'{"id": "", "message": "Queued", "items": []}'
        else:
            resp._content = b'{"message": "Chaos injected error"}'

        return resp


# 1. Enforce a global fallback socket timeout to immediately fail any unmocked socket calls
socket.setdefaulttimeout(1.0)

# 2. Patch Session.send globally so client.ping() cannot escape to live networks
def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    auth_key = fdp.ConsumeUnicodeNoSurrogates(16) or "test-key"
    num_operations = fdp.ConsumeIntInRange(2, 10)

    adapter = ChaosMockAdapter(fdp)
    config = Config(
        api_url="https://api.mailgun.net/v3",
        retry_policy=RetryPolicy(max_retries=0, base_delay=0.0),
    )

    # Patch time.sleep and requests.Session.send to intercept all network traffic
    with patch("time.sleep", return_value=None), \
         patch.object(requests.Session, "send", side_effect=adapter.send):
        try:
            client = Client(auth=("api", auth_key), config=config)
            assert client._session is not None
            client._session.mount("https://", adapter)
            client._session.mount("http://", adapter)
            client._session.mount("", adapter)

            active_domains: list[str] = []

            with client:
                for _ in range(num_operations):
                    op_code = fdp.ConsumeIntInRange(0, 8)

                    # Action 0: Domain Registration
                    if op_code == 0:
                        domain = fdp.ConsumeUnicodeNoSurrogates(16)
                        if domain and "." in domain:
                            try:
                                client.domains.get(domain=domain)
                                active_domains.append(domain)
                            except ApiError:
                                pass

                    # Action 1: Send Message with Cyclic Custom Variables
                    elif op_code == 1 and active_domains:
                        target_domain = fdp.PickValueInList(active_domains)
                        msg_payload: dict[str, Any] = {
                            "to": fdp.ConsumeUnicodeNoSurrogates(16),
                            "from": f"test@{target_domain}",
                            "subject": fdp.ConsumeUnicodeNoSurrogates(16),
                            "text": fdp.ConsumeUnicodeNoSurrogates(64),
                        }
                        if fdp.ConsumeBool():
                            circ: dict[str, Any] = {}
                            circ["self"] = circ
                            msg_payload["v:circular"] = circ

                        try:
                            IdempotencyGuard.generate_key(target_domain, msg_payload)
                        except (TypeError, ValueError):
                            pass

                        try:
                            client.messages.create(domain=target_domain, data=msg_payload)
                        except ApiError:
                            pass

                    # Action 2: Teardown Domain
                    elif op_code == 2 and active_domains:
                        target_domain = active_domains.pop()
                        try:
                            client.domains.delete(domain=target_domain)
                        except ApiError:
                            pass

                    # Action 3: Ping
                    elif op_code == 3:
                        try:
                            client.ping()
                        except ApiError:
                            pass

                    # Action 4: In-Memory Stream Pointer Preservation Sequence
                    elif op_code == 4:
                        raw_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 1024))
                        mem_stream = io.BytesIO(raw_bytes)
                        files = [("attachment", ("file.bin", mem_stream, "application/octet-stream"))]
                        IdempotencyGuard.generate_key("test.com", {"to": "test@test.com"}, files)
                        assert mem_stream.tell() == 0, "Stream pointer corrupted during hash generation"

                    # Action 5: Deep Pagination Shock
                    elif op_code == 5:
                        endpoint = Endpoint(
                            url={"base": "https://api.mailgun.net/v3", "keys": ["events"]},
                            headers={},
                            auth=client.auth,
                            session=client._session,
                        )

                        call_count = 0

                        def mock_paged_get(*args: Any, **kwargs: Any) -> MagicMock:
                            nonlocal call_count
                            call_count += 1
                            m = MagicMock()
                            m.status_code = 200
                            has_next = (call_count < 2) and fdp.ConsumeBool()
                            m.json.return_value = {
                                "items": [{"id": fdp.ConsumeInt(1000)}] if fdp.ConsumeBool() else [],
                                "paging": {
                                    "next": "https://api.mailgun.net/v3/events?page=next"
                                    if has_next
                                    else None
                                },
                            }
                            return m

                        with patch.object(Endpoint, "get", side_effect=mock_paged_get):
                            stream_gen = endpoint.stream(domain="example.com")
                            for _ in range(3):
                                try:
                                    next(stream_gen)
                                except (StopIteration, ApiError):
                                    break

                    # Action 6: SpamGuard Deliverability Parse
                    elif op_code == 6:
                        fuzzed_html = fdp.ConsumeUnicodeNoSurrogates(128)
                        try:
                            report = SpamGuard.check_html(fuzzed_html)
                            assert isinstance(report, dict)
                        except (TypeError, ValueError):
                            pass

                    # Action 7: Timeout Sanitizer Overflow
                    elif op_code == 7:
                        timeout_val = fdp.ConsumeUnicodeNoSurrogates(16)
                        try:
                            SecurityGuard.sanitize_timeout(timeout_val)
                        except (TypeError, ValueError):
                            pass

                    # Action 8: Post-Close Invocation Invariant Check
                    elif op_code == 8:
                        client.close()
                        try:
                            client.ping()
                        except (ApiError, AttributeError, RuntimeError):
                            pass
                        break

        except (
            ApiError,
            MailgunTimeoutError,
            KeyError,
            StopIteration,
            TypeError,
            UnicodeEncodeError,
            ValueError,
        ):
            pass
        except Exception as e:
            raise RuntimeError(f"STATEFUL CRASH: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

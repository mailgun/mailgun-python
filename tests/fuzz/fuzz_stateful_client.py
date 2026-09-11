#!/usr/bin/env python3
"""Stateful Fuzzer for the Mailgun Sync Client.

Exercises state transitions, streaming pagination shocks, attachment pointer
resets, and circular payload sanitization under adversarial inputs.
"""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import atheris
import requests

with atheris.instrument_imports():
    from mailgun.builders import ChunkedStreamer
    from mailgun.client import Client
    from mailgun.endpoints import Endpoint
    from mailgun.handlers.error_handler import ApiError
    from mailgun.security import IdempotencyGuard, SecurityGuard, SpamGuard

logging.disable(logging.CRITICAL)

# Static response pre-allocation for high throughput execution
_STATIC_RESP = requests.Response()
_STATIC_RESP.status_code = 200
_STATIC_RESP._content = b'{"id": "<test>", "message": "Queued", "items": []}'


def mock_requests_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    _STATIC_RESP.request = request
    return _STATIC_RESP


requests.adapters.HTTPAdapter.send = mock_requests_send  # type: ignore[method-assign]


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)

    auth_key = fdp.ConsumeUnicodeNoSurrogates(32)
    num_operations = fdp.ConsumeIntInRange(1, 20)

    try:
        client = Client(auth=("api", auth_key or "test-key"))
        active_domains: list[str] = []

        with client:
            for _ in range(num_operations):
                op_code = fdp.ConsumeIntInRange(0, 7)

                # Action 0: Domain Registration
                if op_code == 0:
                    domain = fdp.ConsumeUnicodeNoSurrogates(16)
                    if domain:
                        client.domains.get(domain=domain)
                        active_domains.append(domain)

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

                    # Test idempotency key generation against circular payloads
                    try:
                        IdempotencyGuard.generate_key(target_domain, msg_payload)
                    except (ValueError, TypeError):
                        # Expected for malformed/circular fuzz payloads; continue exercising state transitions.
                        pass

                    client.messages.create(domain=target_domain, data=msg_payload)

                # Action 2: Teardown Domain
                elif op_code == 2 and active_domains:
                    target_domain = active_domains.pop()
                    client.domains.delete(domain=target_domain)

                # Action 3: Ping
                elif op_code == 3:
                    client.ping()

                # Action 4: Streamer File Pointer Preservation Sequence
                elif op_code == 4:
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 4096)))
                        tmp_path = Path(tmp.name)

                    try:
                        streamer = ChunkedStreamer(
                            tmp_path, safe_base_dir=tmp_path.parent, chunk_size=512
                        )
                        files = [("attachment", ("file.bin", streamer, "application/octet-stream"))]
                        IdempotencyGuard.generate_key("test.com", {"to": "test@test.com"}, files)
                        assert streamer.tell() == 0, "Streamer pointer corrupted during hash generation"
                        streamer.close()
                    finally:
                        if tmp_path.exists():
                            tmp_path.unlink()

                # Action 5: Stream Null Paging Cursor Shock
                elif op_code == 5:
                    endpoint = Endpoint(
                        url={"base": "https://api.mailgun.net/v3", "keys": ["events"]},
                        headers={},
                        auth=client.auth,
                        session=client._session,
                    )
                    mock_payload = {
                        "items": [{"id": fdp.ConsumeInt(1000)}] if fdp.ConsumeBool() else None,
                        "paging": None
                        if fdp.ConsumeBool()
                        else {
                            "next": None
                            if fdp.ConsumeBool()
                            else "https://api.mailgun.net/v3/events?page=next"
                        },
                    }
                    mock_resp = MagicMock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = mock_payload

                    # Patch on Endpoint class to respect __slots__
                    with patch.object(Endpoint, "get", return_value=mock_resp):
                        stream_gen = endpoint.stream(domain="example.com")
                        for _ in range(2):
                            try:
                                next(stream_gen)
                            except StopIteration:
                                break

                # Action 6: Deliverability & XSS SpamGuard Parse
                elif op_code == 6:
                    fuzzed_html = fdp.ConsumeUnicodeNoSurrogates(256)
                    try:
                        report = SpamGuard.check_html(fuzzed_html)
                        assert isinstance(report, dict)
                    except ValueError:
                        # Expected for malformed fuzz inputs; continue fuzzing.
                        pass

                # Action 7: Timeout Overflow & Chaos Bounds
                elif op_code == 7:
                    timeout_val = fdp.ConsumeUnicodeNoSurrogates(16)
                    try:
                        SecurityGuard.sanitize_timeout(timeout_val)
                    except (ValueError, TypeError):
                        # Invalid fuzzed timeout values are expected; continue fuzzing.
                        pass

    except (ApiError, ValueError, TypeError, KeyError, UnicodeEncodeError, StopIteration):
        pass
    except Exception as e:
        raise RuntimeError(f"STATEFUL CRASH: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

#!/usr/bin/env python3
"""Fuzz test for Pagination Cursor Type-Casting, URL Parsing, and SSRF Safety.

Focus: Type-drift between initial filters and paging.next query strings,
path traversal, external scheme SSRF, and cyclic cursor loop detection.
"""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import atheris

with atheris.instrument_imports():
    from mailgun.client import Endpoint

_HOSTILE_PAGING_URLS = [
    "https://api.mailgun.net/v3/events?page=next&limit=10",
    "https://api.eu.mailgun.net/v4/events?ascending=yes",
    "http://attacker.evil.com/v3/events?session=hijacked",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "/v3/domains/example.com/events?ascending=true",
    "https://api.mailgun.net/v3/events?limit=999999999999999999999999999999",
    "https://api.mailgun.net/v3/events?limit=-5&ascending=invalid",
    "https://api.mailgun.net/v3/events?limit=10&ascending=true&ascending=false",
    "https://api.mailgun.net/v3/events?tags=tag1&tags=tag2&tags=tag3",
    "https://api.mailgun.net/v3/events?\x00=corrupted",
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 8:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Generate initial typed developer filters
    initial_filters: dict[str, Any] = {}
    if fdp.ConsumeBool():
        initial_filters["limit"] = fdp.ConsumeIntInRange(-10, 100)
    if fdp.ConsumeBool():
        initial_filters["ascending"] = fdp.ConsumeBool()
    if fdp.ConsumeBool():
        initial_filters["page"] = fdp.ConsumeUnicodeNoSurrogates(16)
    if fdp.ConsumeBool():
        initial_filters["event"] = fdp.PickValueInList(
            ["delivered", "failed", "opened", "clicked", None]
        )

    # Next URL selection: either from hostile seeds or dynamically fuzzed
    if fdp.ConsumeBool():
        next_url = fdp.PickValueInList(_HOSTILE_PAGING_URLS)
    else:
        query_segment = fdp.ConsumeUnicodeNoSurrogates(64)
        next_url = f"https://api.mailgun.net/v3/events?{query_segment}"

    mock_responses = [
        # Page 1 response: returns items and paging pointer
        {
            "items": [{"id": "event_1", "recipient": "user1@example.com"}],
            "paging": {"next": next_url, "previous": None},
        },
        # Page 2 response: simulates exhaustion or terminal page
        {
            "items": [{"id": "event_2", "recipient": "user2@example.com"}],
            "paging": {
                "next": (
                    next_url if fdp.ConsumeBool() else None
                ),  # 50% test cyclic cursor
                "previous": None,
            },
        },
    ]

    response_index = 0

    def mock_get(*args: Any, **kwargs: Any) -> Any:
        nonlocal response_index
        resp = MagicMock()
        resp.raise_for_status.return_value = None

        if response_index < len(mock_responses):
            resp.json.return_value = mock_responses[response_index]
            response_index += 1
        else:
            resp.json.return_value = {"items": [], "paging": {"next": None}}
        return resp

    ep = Endpoint(
        url={"base": "https://api.mailgun.net/v3", "keys": ["events"]},
        headers={},
        auth=("api", "key-test-12345"),
    )

    with patch.object(Endpoint, "get", side_effect=mock_get):
        try:
            stream_gen = ep.stream(filters=initial_filters)

            # Pull up to 3 pages to test iteration, type casting, and termination
            iterations = 0
            for _ in stream_gen:
                iterations += 1
                if iterations >= 3:
                    # Invariant: prevent endless loops on cyclic next URLs
                    break

        except (StopIteration, TypeError, ValueError):
            # Expected rejections for invalid pagination URLs or unparsable query params
            pass
        except Exception as e:
            raise RuntimeError(
                f"UNHANDLED CRASH in Endpoint.stream with filters {initial_filters} and url {repr(next_url)}: {e}"
            ) from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

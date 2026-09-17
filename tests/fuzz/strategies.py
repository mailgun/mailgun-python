#!/usr/bin/env python3
"""Hypothesis strategies for fuzzing the Mailgun SDK.

Generates RFC-compliant and hostile inputs: path traversals, CRLF smuggling,
header prefix mappings (h:, v:, o:), webhook timestamps, and nested JSON payloads.
"""

from typing import Any

import hypothesis.strategies as st

_EVIL_CONTROL_CHARS = [
    "\r\n",
    "\n",
    "\r",
    "\x00",
    "../",
    "..\\",
    "%00",
    "%0d%0a",
    "%2e%2e%2f",
    "%252e%252e%252f",
    "{}",
    "[]",
    "<script>",
    "' OR 1=1 --",
    "\u200b",
    "\ufeff",
    "\u202e",
]

_COMMON_DOMAINS = [
    "example.com",
    "sandbox.mailgun.org",
    "api.mailgun.net",
    "mail.custom-domain.co.uk",
    "xn--eckwd4c7c.xn--zckzah",
]

@st.composite  # type: ignore[untyped-decorator]
def evil_payloads(draw: st.DrawFn) -> str:
    """Generates strings designed to break path sanitizers, headers, and query parsers."""
    base_str = draw(st.text(min_size=0, max_size=64))
    prefix = draw(st.sampled_from(_EVIL_CONTROL_CHARS))
    suffix = draw(st.sampled_from(_EVIL_CONTROL_CHARS))
    return f"{prefix}{base_str}{suffix}"


@st.composite  # type: ignore[untyped-decorator]
def evil_domains(draw: st.DrawFn) -> str:
    """Generates valid and hostile domains (IDN, punycode, path-injected)."""
    choice = draw(st.integers(min_value=0, max_value=3))
    if choice == 0:
        return draw(st.sampled_from(_COMMON_DOMAINS))
    if choice == 1:
        # IDN domain
        return f"xn--{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=3, max_size=12))}.com"
    if choice == 2:
        # Traversal injection in domain
        return f"example.com{draw(st.sampled_from(_EVIL_CONTROL_CHARS))}"
    return draw(st.text(min_size=1, max_size=64))


@st.composite  # type: ignore[untyped-decorator]
def nested_json_strategy(draw: st.DrawFn, max_depth: int = 2) -> Any:
    """Generates nested dictionary/list trees compatible with JSON serialization."""
    if max_depth <= 0:
        return draw(
            st.one_of(
                st.text(max_size=32),
                st.integers(min_value=-10000, max_value=10000),
                st.booleans(),
                st.none(),
            )
        )

    return draw(
        st.one_of(
            st.dictionaries(
                keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=12),
                values=nested_json_strategy(max_depth=max_depth - 1),  # pyright: ignore[reportCallIssue]
                max_size=3,
            ),
            st.lists(nested_json_strategy(max_depth=max_depth - 1), max_size=3),  # pyright: ignore[reportCallIssue]
            st.text(max_size=32),
            st.integers(min_value=-1000, max_value=1000),
            st.booleans(),
            st.none(),
        )
    )


@st.composite  # type: ignore[untyped-decorator]
def get_fuzz_payloads(draw: st.DrawFn) -> dict[str, Any]:
    """Generates complete API request payloads exercising h:, v:, and o: prefixes."""
    payload: dict[str, Any] = {
        "to": draw(st.one_of(st.emails(), st.lists(st.emails(), min_size=1, max_size=3))),
        "from": draw(st.one_of(st.emails(), evil_payloads())),  # pyright: ignore[reportCallIssue]
        "subject": draw(evil_payloads()),  # pyright: ignore[reportCallIssue]
    }

    if draw(st.booleans()):
        payload["text"] = draw(st.text(max_size=128))
    if draw(st.booleans()):
        payload["html"] = draw(st.text(max_size=128))

    # Custom Header (h:)
    if draw(st.booleans()):
        header_key = f"h:{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz-', min_size=1, max_size=16))}"  # pragma: allowlist secret
        payload[header_key] = draw(evil_payloads())  # pyright: ignore[reportCallIssue]

    # Custom Variable (v:)
    if draw(st.booleans()):
        var_key = f"v:{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz_', min_size=1, max_size=16))}"  # pragma: allowlist secret
        payload[var_key] = draw(nested_json_strategy(max_depth=1))  # pyright: ignore[reportCallIssue]

    # Option parameters (o:)
    if draw(st.booleans()):
        payload["o:tag"] = draw(st.lists(st.text(min_size=1, max_size=16), min_size=1, max_size=3))
    if draw(st.booleans()):
        payload["o:tracking"] = draw(st.sampled_from([True, False, "yes", "no"]))
    if draw(st.booleans()):
        payload["o:deliverytime"] = draw(
            st.sampled_from(
                [
                    "Fri, 25 Oct 2026 23:10:10 -0000",
                    "2026-10-25T23:10:10Z",
                    draw(st.integers(min_value=0, max_value=2147483647)),
                ]
            )
        )

    return payload

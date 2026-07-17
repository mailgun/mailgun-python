#!/usr/bin/env python3
"""Hypothesis strategies for fuzzing the Mailgun SDK."""

from typing import Any

import hypothesis.strategies as st


@st.composite  # type: ignore[untyped-decorator]
def evil_payloads(draw: st.DrawFn) -> str:
    """Generates strings designed to break path sanitizers and header parsers."""
    evil_chars = ["\r\n", "\x00", "../", "..\\", "%00", "%0d%0a", "{}"]
    base_str = draw(st.text(min_size=1, max_size=64))

    # Inject evil chars randomly to maximize coverage of sanitization edge cases
    prefix = draw(st.sampled_from(evil_chars))
    suffix = draw(st.sampled_from(evil_chars))

    return f"{prefix}{base_str}{suffix}"


def get_fuzz_payloads() -> st.SearchStrategy[dict[str, Any]]:
    """Strategies for complex API request payloads."""
    return st.fixed_dictionaries(
        {
            "h:X-Fuzz-Header": evil_payloads(),  # pyright: ignore[reportCallIssue]
            "subject": evil_payloads(),  # pyright: ignore[reportCallIssue]
            "to": st.emails(),
        }
    )

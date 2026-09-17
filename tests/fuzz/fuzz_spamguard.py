#!/usr/bin/env python3
"""Fuzz test for the Local SpamGuard Deliverability HTML Parser and Pre-Flight Engine.

Focus: HTML parsing state explosion, unbalanced tags, script/style injection,
zero-width text hiding, boundary payload enforcement (<100KB vs >=100KB),
and SpamReport TypedDict contract verification.
"""

import atexit
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SpamGuard

logging.disable(logging.CRITICAL)

_MALFORMED_HTML_SNIPPETS = [
    '<a href="http://evil.com">Click here</a>',
    '<img src="cid:missing.png" alt="No image">',
    '<div style="display:none;font-size:0px;color:#ffffff;background-color:#ffffff">Hidden Spam</div>',
    '<script>alert("xss")</script>',
    '<iframe src="javascript:alert(1)"></iframe>',
    '<!-- ' * 50 + 'Unclosed Comment',
    '<table' + ' border=1' * 200 + '><tr><td>Deep attr</td></tr></table>',
    '<a href="javascript:void(0)">Spam</a>' * 50,
    '<p>\u200b\u200c\u200dHidden zero-width tokens\ufeff</p>',
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"' + '>' * 100,
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 8:
        return

    fdp = atheris.FuzzedDataProvider(data)

    mode = fdp.ConsumeIntInRange(0, 2)
    if mode == 0:
        # Mode 0: Structured HTML with known deliverability traps
        num_snippets = fdp.ConsumeIntInRange(1, 6)
        parts = [
            fdp.PickValueInList(_MALFORMED_HTML_SNIPPETS)
            for _ in range(num_snippets)
        ]
        html_content = f"<html><body>{''.join(parts)}</body></html>"

    elif mode == 1:
        # Mode 1: Boundary stress test around MAX_HTML_SIZE_BYTES (100,000 bytes)
        size_choice = fdp.ConsumeIntInRange(0, 2)
        if size_choice == 0:
            target_size = 99_950
        elif size_choice == 1:
            target_size = 100_000
        else:
            target_size = 100_050

        base_str = fdp.ConsumeUnicodeNoSurrogates(target_size)
        html_content = f"<html><body><p>{base_str}</p></body></html>"

    else:
        # Mode 2: Unconstrained chaotic Unicode noise
        html_content = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(10, 40000))

    try:
        report: Any = SpamGuard.check_html(html_content)

        # Invariant 1: Return type strictly conforms to SpamReport contract
        if not isinstance(report, dict):
            raise RuntimeError(f"CONTRACT VIOLATION: check_html returned {type(report)}")

        required_keys = {"score", "issues", "is_safe"}
        if not required_keys.issubset(report.keys()):
            raise RuntimeError(f"SCHEMA DEFECT: Missing required keys in SpamReport: {set(report.keys())}")

        # Invariant 2: Score bounded and numeric
        score = report["score"]
        if not isinstance(score, (int, float)) or score < 0:
            raise RuntimeError(f"VALUE ANOMALY: Invalid score returned: {score}")

        # Invariant 3: Issues collection
        if not isinstance(report["issues"], list):
            raise RuntimeError(f"TYPE DRIFT: Issues must be a list, got {type(report['issues'])}")

    except (TypeError, ValueError):
        # Expected rejection for oversized payloads exceeding MAX_HTML_SIZE_BYTES
        pass
    except RecursionError:
        raise RuntimeError("RECURSION EXPLOSION in SpamGuard HTMLParser")
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in SpamGuard.check_html: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

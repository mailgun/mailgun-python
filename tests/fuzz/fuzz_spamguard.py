#!/usr/bin/env python3
"""Fuzz test for the Local SpamGuard Deliverability HTML Parser."""

import logging
import sys

import atheris

with atheris.instrument_imports():
    from mailgun.security import SpamGuard

logging.disable(logging.CRITICAL)


def TestOneInput(data: bytes) -> None:
    # We want varied lengths, but avoid multi-megabyte payloads
    # to maintain high executions-per-second (EPS)
    if not (10 < len(data) < 100_000):
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Generate chaotic HTML (mix of valid tags, malformed attributes, and binary noise)
    html_content = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(10, 50000))

    try:
        # 2. Feed it directly to the static analyzer
        report = SpamGuard.check_html(html_content)

        # 3. Assert the contract of the return type (SpamReport TypedDict)
        if not isinstance(report, dict):
            raise RuntimeError("CRASH: SpamGuard did not return a dictionary.")
        if "score" not in report or "issues" not in report or "is_safe" not in report:
            raise RuntimeError("CRASH: SpamGuard return payload breached TypedDict contract.")

    except (ValueError, TypeError):
        # Normal Python rejections for extremely malformed edge cases
        pass
    except RecursionError:
        raise RuntimeError(
            "CRITICAL SECURITY BUG: Malformed HTML caused a RecursionError in _SpamGuardParser!"
        )
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in SpamGuard: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

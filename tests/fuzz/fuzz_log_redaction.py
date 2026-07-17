#!/usr/bin/env python3
"""Fuzz test for Log Sanitization (ReDoS and Deep Type confusion)."""

import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.filters import RedactingFilter

logging.disable(logging.CRITICAL)


def generate_complex_args(
    fdp: atheris.FuzzedDataProvider, depth: int = 0, state: dict[str, int] | None = None
) -> Any:
    # Recursive generator to test deep dictionary walking logic
    # Now includes structural guardrails to prevent OOM
    if state is None:
        state = {"total_nodes": 0}

    # Increment node counter
    state["total_nodes"] += 1

    # Guardrail: If too deep or too many nodes, return simple string to prune tree
    if depth > 3 or state["total_nodes"] > 500:
        return fdp.ConsumeUnicodeNoSurrogates(16)

    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    elif choice == 1:
        return fdp.ConsumeInt(1000)
    elif choice == 2:
        return [
            generate_complex_args(fdp, depth + 1, state)
            for _ in range(fdp.ConsumeIntInRange(1, 3))
        ]
    elif choice == 3:
        return {
            fdp.ConsumeUnicodeNoSurrogates(16): generate_complex_args(
                fdp, depth + 1, state
            )
        }
    else:
        return None


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    filter_instance = RedactingFilter()

    args: tuple[Any, ...]

    # Route 1: ReDoS (Regular Expression Denial of Service) Attack
    if fdp.ConsumeBool():
        # Inject massive repetitive strings to test if the regex engine hangs
        # e.g., "api_key=api_key=api_key=..."
        poison = fdp.PickValueInList(["Bearer ", "api_key=", "password:", "token="])
        msg = (poison * fdp.ConsumeIntInRange(10, 100)) + fdp.ConsumeUnicodeNoSurrogates(
            200
        )
        args = ()

    # Route 2: Deeply Nested Type Confusion Attack
    else:
        msg = fdp.ConsumeUnicodeNoSurrogates(64)
        # Create complex nested structures (tuples of dicts of lists)
        args = tuple(
            generate_complex_args(fdp) for _ in range(fdp.ConsumeIntInRange(1, 5))
        )
        # If msg is massive, truncate it before creating LogRecord
        if len(msg) > 1024:
            msg = msg[:1024]

    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="fake.py",
            lineno=1,
            msg=msg,
            args=args,
            exc_info=None,
        )
    except Exception:
        return

    try:
        # Target: Does the redactor crash on nested lists, ints, or ReDoS?
        filter_instance.filter(record)
    except (TypeError, ValueError):
        # Expected for malformed fuzz-generated inputs; not treated as security crashes.
        pass
    except Exception as e:
        # Any other exception (AttributeError, RecursionError) is a security failure
        raise RuntimeError(f"CRASH in RedactingFilter: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

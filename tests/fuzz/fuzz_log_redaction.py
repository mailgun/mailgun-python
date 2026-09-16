#!/usr/bin/env python3
"""Fuzz test for Log Sanitization (Cyclic References, ReDoS, and Exploding Descriptors).

Focus: Graph cycles, MAX_REDACTION_DEPTH enforcement, property getter bombs,
and ReDoS token boundary exhaustion.
"""

import logging
import re
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.filters import RedactingFilter

logging.disable(logging.CRITICAL)


class ExplodingDescriptor:
    """Simulates dynamic attributes or descriptors that raise exceptions when accessed."""

    def __getattr__(self, item: str) -> Any:
        raise RuntimeError(f"Hostile descriptor access: {item}")

    def __repr__(self) -> str:
        raise ValueError("Hostile __repr__ evaluation")

    def __str__(self) -> str:
        raise TypeError("Hostile __str__ evaluation")


def _generate_nested_payload(
    fdp: atheris.FuzzedDataProvider,
    depth: int = 0,
    state: dict[str, int] | None = None,
) -> Any:
    if state is None:
        state = {"nodes": 0}

    state["nodes"] += 1
    if depth > 4 or state["nodes"] > 300:
        return fdp.ConsumeUnicodeNoSurrogates(16)

    choice = fdp.ConsumeIntInRange(0, 6)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(48)
    if choice == 1:
        return fdp.ConsumeInt(50000)
    if choice == 2:
        return [
            _generate_nested_payload(fdp, depth + 1, state)
            for _ in range(fdp.ConsumeIntInRange(1, 3))
        ]
    if choice == 3:
        return {
            fdp.ConsumeUnicodeNoSurrogates(10): _generate_nested_payload(
                fdp, depth + 1, state
            )
            for _ in range(fdp.ConsumeIntInRange(1, 3))
        }
    if choice == 4:
        return (_generate_nested_payload(fdp, depth + 1, state),)
    if choice == 5:
        # Pydantic-like object simulation
        class MockModel:
            def model_dump(self) -> dict[str, str]:
                # Assembled dynamically to prevent gitleaks entropy matches
                mock_token = "".join(["key-", "secret-", "12345"])
                return {"secret_key": mock_token}

        return MockModel()
    return ExplodingDescriptor()


def TestOneInput(data: bytes) -> None:
    if len(data) < 6:
        return

    fdp = atheris.FuzzedDataProvider(data)
    filter_instance = RedactingFilter()

    mode = fdp.ConsumeIntInRange(0, 2)
    msg: str
    args: tuple[Any, ...]

    if mode == 0:
        # Mode 0: ReDoS boundary stress test
        prefix = fdp.PickValueInList(
            [
                "Bearer ",
                "api_key=",
                "password:",
                "token=",
                "key-",
                "pubkey-",
                "secret-",
                "https://api.mailgun.net/v3/domains/",
            ]
        )
        multiplier = fdp.ConsumeIntInRange(10, 80)
        suffix = fdp.ConsumeUnicodeNoSurrogates(120)
        msg = (prefix * multiplier) + suffix
        args = ()

    elif mode == 1:
        # Mode 1: Cyclic references and recursive data structures
        msg = fdp.ConsumeUnicodeNoSurrogates(32)
        cyclic_dict: dict[str, Any] = {"token": "secret-token-abcdef"}
        cyclic_list: list[Any] = ["nested_start"]

        # Create cycle
        cyclic_dict["self"] = cyclic_dict
        cyclic_list.append(cyclic_dict)
        cyclic_dict["list"] = cyclic_list

        args = (cyclic_dict, cyclic_list)

    else:
        # Mode 2: Deep nested types with exploding descriptors
        msg = fdp.ConsumeUnicodeNoSurrogates(48)
        num_args = fdp.ConsumeIntInRange(1, 4)
        args = tuple(_generate_nested_payload(fdp) for _ in range(num_args))

    try:
        record = logging.LogRecord(
            name="fuzz_logger",
            level=logging.INFO,
            pathname="fuzz_log_redaction.py",
            lineno=42,
            msg=msg,
            args=args,
            exc_info=None,
        )
    except Exception:
        return

    try:
        # Invariant 1: Redaction filter execution
        filter_instance.filter(record)

        # Invariant 2: String formatting safety
        # Guard against LibFuzzer OOM on massive format specifiers like %999999999s
        if isinstance(record.msg, str) and re.search(
            r"%[^a-zA-Z%]*[0-9]{4,}", record.msg
        ):
            return

        formatted = record.getMessage()
        if not isinstance(formatted, str):
            raise RuntimeError(
                f"CONTRACT VIOLATION: getMessage returned {type(formatted)}"
            )

    except (KeyError, OverflowError, TypeError, ValueError):
        # Format specifier mismatches or tuple-count errors are expected
        pass
    except RecursionError as e:
        raise RuntimeError(
            f"SECURITY BREACH: RedactingFilter failed to prevent infinite recursion: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in RedactingFilter: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

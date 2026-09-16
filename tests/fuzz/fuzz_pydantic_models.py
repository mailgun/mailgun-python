#!/usr/bin/env python3
"""Fuzz test for Pydantic v2 SendMessageSchema validation, ReDoS, and Type Boundaries.

Focus: Multi-recipient parsing, RFC 5322 display names, CRLF header injection,
custom parameter prefixes (h:, v:, o:), delivery time boundaries, and JSON variables.
"""

import atexit
import json
import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from pydantic import ValidationError

    from mailgun.ext.pydantic.models import SendMessageSchema

logging.disable(logging.CRITICAL)

_MALICIOUS_RECIPIENTS = [
    "user@example.com",
    "Admin <admin@example.com>",
    "evil\r\nBcc: victim@target.com",
    "user@localhost",
    "test@[127.0.0.1]",
    "\"Recipient with quotes\" <recipient@example.com>",
    "user+tag@domain.co.uk",
    "a" * 255 + "@long.domain.com",
    "user@" + "sub." * 50 + "com",
    "user\x00@nullbyte.com",
    "",
]

_HEADER_PREFIXES = ["h:X-Mailgun-Tag", "v:my_custom_var", "o:tracking", "o:tag", "custom"]


def _generate_fuzzed_recipient(fdp: atheris.FuzzedDataProvider) -> Any:
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.PickValueInList(_MALICIOUS_RECIPIENTS)
    if choice == 1:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 2:
        return [
            fdp.PickValueInList(_MALICIOUS_RECIPIENTS)
            for _ in range(fdp.ConsumeIntInRange(1, 4))
        ]
    if choice == 3:
        return fdp.ConsumeInt(10000)
    return None


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)

    to_val = _generate_fuzzed_recipient(fdp)
    from_val = (
        fdp.PickValueInList(_MALICIOUS_RECIPIENTS)
        if fdp.ConsumeBool()
        else fdp.ConsumeUnicodeNoSurrogates(48)
    )
    subject_val = (
        fdp.ConsumeUnicodeNoSurrogates(64) if fdp.ConsumeBool() else None
    )
    text_val = (
        fdp.ConsumeUnicodeNoSurrogates(128) if fdp.ConsumeBool() else None
    )
    html_val = (
        fdp.ConsumeUnicodeNoSurrogates(128) if fdp.ConsumeBool() else None
    )

    # Custom parameter mutations (testing h:, v:, o: prefix handling & CRLF rejection)
    custom_params: dict[str, Any] = {}
    num_params = fdp.ConsumeIntInRange(0, 6)
    for _ in range(num_params):
        if fdp.ConsumeBool():
            prefix = fdp.PickValueInList(_HEADER_PREFIXES)
            key = f"{prefix}_{fdp.ConsumeUnicodeNoSurrogates(8)}"
        else:
            key = fdp.ConsumeUnicodeNoSurrogates(16)

        val_type = fdp.ConsumeIntInRange(0, 4)
        if val_type == 0:
            val: Any = fdp.ConsumeUnicodeNoSurrogates(64)
        elif val_type == 1:
            val = fdp.ConsumeInt(500000)
        elif val_type == 2:
            val = fdp.ConsumeBool()
        elif val_type == 3:
            val = {"nested": fdp.ConsumeUnicodeNoSurrogates(16)}
        else:
            val = None

        custom_params[key] = val

    try:
        model = SendMessageSchema(
            to=to_val,
            from_=from_val,
            subject=subject_val,
            text=text_val,
            html=html_val,
            custom_params=custom_params,
        )

        # Invariant checks on successfully validated models
        dumped = model.model_dump()
        if not isinstance(dumped, dict):
            raise RuntimeError(f"Contract violation: model_dump returned {type(dumped)}")

        # Ensure no raw CRLF leaks through successfully validated fields
        for field in ("from_", "subject"):
            field_val = dumped.get(field)
            if isinstance(field_val, str) and ("\r" in field_val or "\n" in field_val):
                raise RuntimeError(f"CRLF injection leak in model field {field}: {repr(field_val)}")

    except (ValidationError, ValueError, TypeError):
        # Expected defensive rejections from Pydantic validators
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in SendMessageSchema: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

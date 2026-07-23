#!/usr/bin/env python3
"""Fuzz test for Pydantic v2 SendMessageSchema validation and CRLF defenses."""

import sys
from typing import Any
import atheris

with atheris.instrument_imports():
    from pydantic import ValidationError
    from mailgun.ext.pydantic.models import SendMessageSchema


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    try:
        # Fuzz core message fields
        to_val: Any = fdp.ConsumeUnicodeNoSurrogates(60)
        from_val: Any = fdp.ConsumeUnicodeNoSurrogates(60)

        # Optionally pass lists for recipients
        if fdp.ConsumeBool():
            to_val = [fdp.ConsumeUnicodeNoSurrogates(30), fdp.ConsumeUnicodeNoSurrogates(30)]

        text_val = fdp.ConsumeUnicodeNoSurrogates(200) if fdp.ConsumeBool() else None
        html_val = fdp.ConsumeUnicodeNoSurrogates(200) if fdp.ConsumeBool() else None

        # Fuzz custom parameters (testing prefix validation and CRLF detection)
        num_params = fdp.ConsumeIntInRange(0, 5)
        custom_params = {}
        for _ in range(num_params):
            k = fdp.ConsumeUnicodeNoSurrogates(20)
            v = fdp.ConsumeUnicodeNoSurrogates(50)
            custom_params[k] = v

        # Execute Pydantic model validation
        SendMessageSchema(
            to=to_val,
            from_=from_val,
            text=text_val,
            html=html_val,
            custom_params=custom_params,
        )

    except (ValidationError, ValueError, TypeError):
        # Expected schema rejection for malformed inputs or security triggers
        pass


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

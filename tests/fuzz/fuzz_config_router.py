#!/usr/bin/env python3

import logging
import sys

import atheris

with atheris.instrument_imports():
    from mailgun.config import Config
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)
    fuzzed_base_url = fdp.ConsumeUnicodeNoSurrogates(128)

    try:
        config = Config(api_url=fuzzed_base_url)
    except (TypeError, ValueError):
        return

    endpoint_key = fdp.ConsumeUnicodeNoSurrogates(128)

    try:
        url_data, headers = config[endpoint_key]

        if not isinstance(url_data, dict) or not isinstance(headers, dict):
            raise RuntimeError("CRASH: Config output breached dict contract.")

        if "base" not in url_data or "keys" not in url_data:
            raise RuntimeError("CRASH: Config output missing 'base' or 'keys'.")

        if not isinstance(url_data["base"], str):
            raise RuntimeError("CRASH: Config base URL is not a string.")

    except (ApiError, TypeError, ValueError):
        # Expected for malformed fuzz input; ignore and continue fuzzing.
        pass
    except KeyError as e:
        if "Invalid endpoint key" in str(e):
            return

        raise RuntimeError(f"CRASH: Unexpected KeyError in router fallback: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

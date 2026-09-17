#!/usr/bin/env python3
"""Fuzzer for Route Resolution, Path Injection, and Config Normalization."""

import logging
import sys

import atheris

with atheris.instrument_imports():
    from mailgun import routes
    from mailgun.config import Config
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

_KNOWN_ROUTES = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)
    fuzzed_base_url = (
        fdp.ConsumeUnicodeNoSurrogates(128)
        if fdp.ConsumeBool()
        else fdp.PickValueInList(
            [
                "https://api.mailgun.net",
                "https://api.eu.mailgun.net/v3",
                "http://localhost:8080",
                "https://evil.com#api.mailgun.net",
                "https://user:pass@api.mailgun.net",  # pragma: allowlist secret
                "ftp://api.mailgun.net",
                "/v3/relative/path",
            ]
        )
    )

    try:
        config = Config(api_url=fuzzed_base_url)
    except (TypeError, ValueError):
        return

    # 50% test known route with chaotic interpolations, 50% test arbitrary keys
    if fdp.ConsumeBool() and _KNOWN_ROUTES:
        endpoint_key = fdp.PickValueInList(_KNOWN_ROUTES)
    else:
        endpoint_key = fdp.ConsumeUnicodeNoSurrogates(64)

    try:
        url_data, headers = config[endpoint_key]

        # Invariant 1: Type contracts
        if not isinstance(url_data, dict) or not isinstance(headers, dict):
            raise RuntimeError("CRASH: Config output breached dict contract.")

        # Invariant 2: Structure integrity
        if "base" not in url_data or "keys" not in url_data:
            raise RuntimeError("CRASH: Config output missing 'base' or 'keys'.")

        if not isinstance(url_data["base"], str) or not isinstance(url_data["keys"], list):
            raise RuntimeError("CRASH: Config base or keys wrong data type.")

        # Invariant 3: Known routes must never raise unhandled exceptions
        if endpoint_key in _KNOWN_ROUTES and not url_data["keys"]:
            raise RuntimeError(f"CRASH: Known route '{endpoint_key}' resolved to empty keys.")

    except (ApiError, TypeError, ValueError):
        pass
    except KeyError as e:
        error_msg = str(e)
        if "Invalid API endpoint requested" in error_msg or "Invalid endpoint key" in error_msg:
            return
        raise RuntimeError(f"CRASH: Unexpected KeyError in router fallback: {e}") from e
    except Exception as e:
        raise RuntimeError(f"UNHANDLED ROUTER CRASH: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

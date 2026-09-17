#!/usr/bin/env python3
"""Fuzz test for dynamic HTTP header merging, CRLF injection, and multi-type kwarg filtering."""

import logging
import sys
from typing import Any

import atheris


with atheris.instrument_imports():
    from mailgun.endpoints import BaseEndpoint
    from mailgun.security import SecretAuth

logging.disable(logging.CRITICAL)


def _generate_header_value(fdp: atheris.FuzzedDataProvider) -> Any:
    """Generate diverse header value types including injection probes and non-strings."""
    mode = fdp.ConsumeIntInRange(0, 5)
    if mode == 0:
        # CRLF injection probe
        probe = fdp.PickValueInList(["\r\n", "\n", "\r", "\r\nSet-Cookie: evil=1", "\x00"])
        return f"{fdp.ConsumeUnicodeNoSurrogates(10)}{probe}{fdp.ConsumeUnicodeNoSurrogates(10)}"
    if mode == 1:
        # Standard ASCII header string
        return fdp.ConsumeUnicodeNoSurrogates(32)
    if mode == 2:
        # Numeric / boolean type confusion
        return fdp.ConsumeInt(65535) if fdp.ConsumeBool() else fdp.ConsumeBool()
    if mode == 3:
        # Lists / tuples of values
        return [fdp.ConsumeUnicodeNoSurrogates(8) for _ in range(fdp.ConsumeIntInRange(1, 4))]
    if mode == 4:
        # Empty string or whitespace
        return fdp.PickValueInList(["", "   ", "\t", "Bearer "])
    return None


def TestOneInput(data: bytes) -> None:
    if len(data) < 6:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Generate base headers for endpoint instantiation
    base_headers: dict[str, Any] = {}
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        header_key = fdp.PickValueInList(
            [
                "User-Agent",
                "Authorization",
                "Content-Type",
                "X-Mailgun-Tag",
                "X-Mailgun-Variables",
                fdp.ConsumeUnicodeNoSurrogates(12),
            ]
        )
        base_headers[header_key] = _generate_header_value(fdp)

    endpoint = BaseEndpoint(
        auth=SecretAuth(("api", "key-test")),
        url={"base": "https://api.mailgun.net/v3", "keys": []},
        headers=base_headers,
    )

    # 2. Build runtime kwargs to pass into _merge_headers
    kwargs: dict[str, Any] = {}

    # Case collisions and override testing
    if fdp.ConsumeBool():
        merged_headers: dict[str, Any] = {}
        for _ in range(fdp.ConsumeIntInRange(1, 8)):
            header_key = fdp.PickValueInList(
                [
                    "user-agent",
                    "USER-AGENT",
                    "authorization",
                    "AUTHORIZATION",
                    "content-type",
                    "Content-Type",
                    "x-mailgun-tag",
                    fdp.ConsumeUnicodeNoSurrogates(16),
                ]
            )
            merged_headers[header_key] = _generate_header_value(fdp)
        kwargs["headers"] = merged_headers

    # HTTP transport kwargs injection
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        prop_key = fdp.PickValueInList(
            ["timeout", "verify", "proxies", "params", "allow_redirects", fdp.ConsumeUnicodeNoSurrogates(10)]
        )
        prop_val: Any
        val_mode = fdp.ConsumeIntInRange(0, 3)
        if val_mode == 0:
            prop_val = fdp.ConsumeFloat()
        elif val_mode == 1:
            prop_val = fdp.ConsumeBool()
        elif val_mode == 2:
            prop_val = fdp.ConsumeUnicodeNoSurrogates(20)
        else:
            prop_val = {"https": fdp.ConsumeUnicodeNoSurrogates(20)}
        kwargs[prop_key] = prop_val

    try:
        result = endpoint._merge_headers(kwargs)
        if result is not None and not isinstance(result, (dict, type(None))):
            raise RuntimeError(f"Unexpected return type from _merge_headers: {type(result)}")
    except (TypeError, ValueError, UnicodeEncodeError):
        # Graceful input rejections are expected
        pass
    except Exception as exc:
        raise RuntimeError(
            f"Unhandled exception during _merge_headers:\n"
            f"Base headers: {base_headers!r}\n"
            f"Kwargs:       {kwargs!r}\n"
            f"Exception:    {type(exc).__name__}: {exc}"
        ) from exc


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

#!/usr/bin/env python3
"""Fuzzer for Core SDK Client, Context Managers, Dynamic Routing, and Fallbacks."""

import json
import logging
import sys
from typing import Any

import atheris
import requests

with atheris.instrument_imports():
    from mailgun import routes
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError

logging.disable(logging.CRITICAL)

_VALID_ENDPOINTS = list(routes.EXACT_ROUTES.keys()) + list(routes.PREFIX_ROUTES.keys())


def _generate_chaotic_file_payload(
    fdp: atheris.FuzzedDataProvider,
) -> list[tuple[str, tuple[str, bytes, str]]]:
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for _ in range(fdp.ConsumeIntInRange(1, 3)):
        filename = (
            fdp.ConsumeUnicodeNoSurrogates(32)
            if fdp.ConsumeBool()
            else fdp.PickValueInList(
                [
                    "../../../etc/passwd",
                    ".env",
                    "payload.exe\x00.jpg",
                    "＼．．／＼．．／.txt",
                ]
            )
        )
        content = fdp.ConsumeBytes(64)
        mime_type = fdp.PickValueInList(
            ["application/json", "text/plain", "image/png", fdp.ConsumeUnicodeNoSurrogates(16)]
        )
        files.append(("attachment", (filename, content, mime_type)))
    return files


def mock_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    resp = requests.Response()
    resp.status_code = 200
    resp._content = b'{"message": "client fuzz mock"}'
    return resp


requests.adapters.HTTPAdapter.send = mock_send  # type: ignore[method-assign]


def TestOneInput(data: bytes) -> None:
    if len(data) < 15:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 70% valid endpoints, 30% arbitrary attribute access for default_handler probing
    if fdp.ConsumeBool() or not _VALID_ENDPOINTS:
        target_attr = fdp.ConsumeUnicodeNoSurrogates(24) or "messages"
    else:
        target_attr = fdp.PickValueInList(_VALID_ENDPOINTS)

    method_name = fdp.PickValueInList(["get", "post", "put", "delete"])
    domain = fdp.ConsumeUnicodeNoSurrogates(16) or "test.mailgun.org"

    try:
        with Client(auth=("api", "test-key")) as client:
            endpoint = getattr(client, target_attr, None)
            if endpoint is None:
                return

            action = getattr(endpoint, method_name, None)
            if action is None:
                return

            if fdp.ConsumeBool():
                action(domain=domain, files=_generate_chaotic_file_payload(fdp))
            else:
                action(
                    domain=domain,
                    data={"to": fdp.ConsumeUnicodeNoSurrogates(16), "url": "https://callback.com"},
                )

    except (
        ApiError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        requests.RequestException,
    ):
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Client execution: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

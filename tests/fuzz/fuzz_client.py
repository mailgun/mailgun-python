#!/usr/bin/env python3

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
    num_files = fdp.ConsumeIntInRange(1, 3)

    for _ in range(num_files):
        filename = (
            fdp.ConsumeUnicodeNoSurrogates(32)
            if fdp.ConsumeBool()
            else fdp.PickValueInList(
                [
                    "../../../etc/passwd",
                    ".env",
                    "C:\\Windows\\System32\\cmd.exe",
                    "payload.exe\x00.jpg",
                    "＼．．／＼．．／.txt",
                ]
            )
        )

        content = (
            fdp.ConsumeBytes(128)
            if fdp.ConsumeBool()
            else fdp.ConsumeUnicodeNoSurrogates(128).encode("utf-8", errors="ignore")
        )

        mime_type = fdp.PickValueInList(
            [
                "application/json",
                "application/x-php",
                "image/png",
                "multipart/mixed; boundary=--evil",
                "text/plain",
                fdp.ConsumeUnicodeNoSurrogates(16),
            ]
        )

        files.append(("attachment", (filename, content, mime_type)))

    return files


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return
    fdp = atheris.FuzzedDataProvider(data)

    target_attr = fdp.PickValueInList(_VALID_ENDPOINTS)
    method_name = fdp.PickValueInList(["post", "put"])
    domain = (
        fdp.ConsumeUnicodeNoSurrogates(16)
        if fdp.ConsumeBool()
        else "test.mailgun.org"
    )

    client = Client(auth=("api", "test-key"))

    try:
        endpoint = getattr(client, target_attr)
        action = getattr(endpoint, method_name)

        if fdp.ConsumeBool():
            action(domain=domain, files=_generate_chaotic_file_payload(fdp))
        else:
            action(domain=domain, data={"to": fdp.ConsumeUnicodeNoSurrogates(16)})

    except (
        ApiError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        requests.RequestException,
    ):
        # Expected for malformed fuzz inputs; ignore to keep fuzzing and let
        # only unexpected exceptions fail via the generic handler below.
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Client Multipart execution: {e}") from e


def mock_send(
    self: requests.adapters.HTTPAdapter,
    request: requests.PreparedRequest,
    *args: Any,
    **kwargs: Any,
) -> requests.Response:
    resp = requests.Response()
    resp.status_code = 200
    resp._content = b"{}"
    return resp


if __name__ == "__main__":
    requests.adapters.HTTPAdapter.send = mock_send  # type: ignore[method-assign]

    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

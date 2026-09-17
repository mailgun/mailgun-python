#!/usr/bin/env python3
"""Fuzz test for Network Resilience, Corrupted Chunked Streams, and Evil Server injection."""

import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import atheris
import requests


with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.handlers.error_handler import ApiError, MailgunTimeoutError

logging.disable(logging.CRITICAL)

_STATUS_CODES = [200, 301, 302, 400, 429, 500, 502, 503, 504]
_HTTP_METHODS = ["delete", "get", "post", "put"]


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    client = Client(auth=("api", "test-key"))
    original_send = requests.Session.send

    def evil_send(self: requests.Session, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        # Inject network-level transport faults
        if fdp.ConsumeBool():
            exceptions = [
                requests.exceptions.ConnectionError("Fuzzed Drop"),
                requests.exceptions.Timeout("Fuzzed Read Timeout"),
                requests.exceptions.TooManyRedirects("Infinite Redirect Loop"),
                requests.exceptions.ChunkedEncodingError("Corrupted Chunk Framing"),
                requests.exceptions.ContentDecodingError("Corrupted Zlib/Gzip Stream"),
            ]
            raise fdp.PickValueInList(exceptions)

        # Server response injection
        status = fdp.PickValueInList(_STATUS_CODES)
        headers: dict[str, str] = {
            "content-type": fdp.PickValueInList(
                ["application/json", "text/html", "application/octet-stream", "image/png"]
            ),
            "content-length": str(fdp.ConsumeIntInRange(-1000, 20000)),
        }

        # Hostile Retry-After injection
        if fdp.ConsumeBool():
            headers["Retry-After"] = (
                fdp.ConsumeUnicodeNoSurrogates(16)
                if fdp.ConsumeBool()
                else str(fdp.ConsumeFloat())
            )

        # Redirect loop simulation
        if status in (301, 302):
            headers["Location"] = fdp.PickValueInList(
                ["https://api.mailgun.net/v3/messages", "http://127.0.0.1:80", "/relative/loop"]
            )

        mock_response = requests.Response()
        mock_response.status_code = status
        mock_response._content = fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 2048))
        mock_response.headers.update(headers)
        mock_response.request = request
        mock_response.url = request.url or "https://api.mailgun.net/v3/messages"

        return mock_response

    requests.Session.send = evil_send  # type: ignore[method-assign]

    with Path(os.devnull).open("w") as devnull, contextlib.redirect_stdout(
        devnull
    ), contextlib.redirect_stderr(devnull):
        try:
            target_method = fdp.PickValueInList(_HTTP_METHODS)
            client.messages.api_call(
                method=target_method,
                url=fdp.ConsumeUnicodeNoSurrogates(40) or "https://api.mailgun.net/v3/messages",
                data={"message": fdp.ConsumeUnicodeNoSurrogates(20)},
            )
        except (
            ApiError,
            MailgunTimeoutError,
            TypeError,
            ValueError,
            UnicodeEncodeError,
            requests.RequestException,
            json.JSONDecodeError,
        ):
            pass
        except Exception as exc:
            raise RuntimeError(f"Unhandled crash during evil server simulation: {type(exc).__name__}: {exc}") from exc
        finally:
            requests.Session.send = original_send  # type: ignore[method-assign]
            if hasattr(client, "close"):
                client.close()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

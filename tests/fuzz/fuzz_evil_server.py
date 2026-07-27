#!/usr/bin/env python3
"""Fuzz test for Network Resilience and 'Evil Server' payload handling (Sync/Requests)."""

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


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    client = Client(auth=("api", "test-key"))

    # Save original to restore later
    original_send = requests.Session.send

    def evil_send(self: requests.Session, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        if fdp.ConsumeBool():
            exceptions = [
                requests.exceptions.ConnectionError("Fuzzed Connection Drop"),
                requests.exceptions.Timeout("Fuzzed Timeout"),
                requests.exceptions.TooManyRedirects("Infinite Redirect Loop"),
                requests.exceptions.ChunkedEncodingError("Fuzzed Chunk Error"),
            ]
            raise fdp.PickValueInList(exceptions)

        # SYNC EVIL PAYLOAD INJECTION
        status = fdp.PickValueInList([200, 429, 500, 502, 503, 504])

        headers = {
            "content-type": fdp.PickValueInList(["application/json", "image/png", "text/html"]),
            "content-length": str(fdp.ConsumeIntInRange(-100, 10000)),
            "Retry-After": (
                fdp.ConsumeUnicodeNoSurrogates(16)
                if fdp.ConsumeBool()
                else str(fdp.ConsumeFloat())
            )
        }

        garbage_bytes = fdp.ConsumeBytes(1024)

        # Create the mock standard requests.Response
        mock_response = requests.Response()
        mock_response.status_code = status
        mock_response._content = garbage_bytes
        mock_response.headers.update(headers)
        mock_response.request = request

        return mock_response

    # Monkeypatch the session
    requests.Session.send = evil_send  # type: ignore[method-assign]

    with Path(os.devnull).open("w") as devnull, contextlib.redirect_stdout(
        devnull
    ), contextlib.redirect_stderr(devnull):
        try:
            client.messages.api_call(
                method=fdp.PickValueInList(["delete", "get", "post", "put"]),
                url=fdp.ConsumeUnicodeNoSurrogates(30) or "https://api.mailgun.net/v3/messages",
            )
        except (
                ApiError,
                MailgunTimeoutError,
                TypeError,
                ValueError,
                requests.RequestException,
                json.JSONDecodeError,
        ):
            # Expected during fuzzing: malformed inputs and injected network faults.
            pass
        except Exception as e:
            raise RuntimeError(f"SDK crashed handling Sync Evil Server response: {e}") from e
        finally:
            # Restore to prevent test pollution
            requests.Session.send = original_send  # type: ignore[method-assign]
            if hasattr(client, "close"):
                client.close()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

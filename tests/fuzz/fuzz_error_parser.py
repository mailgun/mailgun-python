#!/usr/bin/env python3
"""Fuzz test for Semantic Error Response Deserialization (HTTPX and Requests dual-engine)."""

import json
import logging
import sys

import atheris
import requests

from mailgun._httpx_compat import httpx as compat_httpx


with atheris.instrument_imports():
    from mailgun.handlers.error_handler import ApiError, DeliverabilityError, MailgunTimeoutError

logging.disable(logging.CRITICAL)

_STATUS_CODES = [400, 401, 402, 403, 404, 409, 413, 422, 429, 500, 502, 503, 504]


def _build_fuzzed_error_content(fdp: atheris.FuzzedDataProvider) -> bytes:
    """Generate valid, invalid, and boundary Mailgun error response payloads."""
    payload_type = fdp.ConsumeIntInRange(0, 4)

    if payload_type == 0:
        # Standard Mailgun error structure
        return json.dumps({
            "message": fdp.ConsumeUnicodeNoSurrogates(64),
            "details": [fdp.ConsumeUnicodeNoSurrogates(32) for _ in range(fdp.ConsumeIntInRange(0, 3))],
        }).encode("utf-8")

    if payload_type == 1:
        # Single error key or legacy dictionary format
        return json.dumps({
            "error": fdp.ConsumeUnicodeNoSurrogates(64),
            "code": fdp.ConsumeInt(1000),
        }).encode("utf-8")

    if payload_type == 2:
        # Array-wrapped errors
        return json.dumps([
            {"message": fdp.ConsumeUnicodeNoSurrogates(32)},
            {"reason": fdp.ConsumeUnicodeNoSurrogates(32)},
        ]).encode("utf-8")

    if payload_type == 3:
        # Non-JSON HTML / XML error page (Cloudflare/Nginx gateway crashes)
        return (
            b"<html><head><title>502 Bad Gateway</title></head><body>"
            + fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 256))
            + b"</body></html>"
        )

    # Pure random binary bytes
    return fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024))


def TestOneInput(data: bytes) -> None:
    if len(data) < 6:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. DeliverabilityError fuzzing
    if fdp.ConsumeBool():
        try:
            score = fdp.ConsumeFloat()
            issues = [
                fdp.ConsumeUnicodeNoSurrogates(24)
                for _ in range(fdp.ConsumeIntInRange(0, 20))
            ]
            err = DeliverabilityError(score=score, issues=issues)
            _ = str(err)
            _ = repr(err)
        except (ValueError, TypeError, OverflowError):
            # Expected for malformed fuzz inputs; continue fuzzing other paths.
            pass

    # 2. MailgunTimeoutError formatting
    if fdp.ConsumeBool():
        try:
            timeout_err = MailgunTimeoutError(fdp.ConsumeUnicodeNoSurrogates(32))
            _ = str(timeout_err)
        except (ValueError, TypeError):
            # Expected for malformed fuzz inputs; continue fuzzing other paths.
            pass

    # 3. HTTP Response Error Deserialization (HTTPX & Requests)
    status_code = fdp.PickValueInList(_STATUS_CODES)
    content = _build_fuzzed_error_content(fdp)
    raw_content_type = fdp.PickValueInList(
        [
            "application/json",
            "application/json; charset=utf-8",
            "text/html",
            "text/plain",
            fdp.ConsumeUnicodeNoSurrogates(16),
        ]
    )
    # Ensure header values conform to valid ASCII per HTTP header specifications
    content_type = raw_content_type.encode("ascii", "replace").decode("ascii")

    # HTTPX response path
    httpx_headers = {"content-type": content_type}
    if status_code == 429 and fdp.ConsumeBool():
        httpx_headers["retry-after"] = str(fdp.ConsumeIntInRange(0, 300))

    httpx_resp = compat_httpx.Response(
        status_code=status_code,
        headers=httpx_headers,
        content=content,
        request=compat_httpx.Request("POST", "https://api.mailgun.net/v3/messages"),
        )

    try:
        api_error_httpx = ApiError(httpx_resp)
        _ = str(api_error_httpx)
        _ = repr(api_error_httpx)
        _ = getattr(api_error_httpx, "status_code", None)
        _ = getattr(api_error_httpx, "message", None)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Leaked raw decoding exception in HTTPX ApiError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"ApiError crashed unexpectedly with HTTPX: {e}") from e

    # Requests response path
    req_resp = requests.Response()
    req_resp.status_code = status_code
    req_resp.headers.update({"content-type": content_type})
    req_resp._content = content
    req_resp.url = "https://api.mailgun.net/v3/messages"

    try:
        api_error_req = ApiError(req_resp)
        _ = str(api_error_req)
        _ = repr(api_error_req)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Leaked raw decoding exception in Requests ApiError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"ApiError crashed unexpectedly with Requests: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

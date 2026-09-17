#!/usr/bin/env python3
"""Fuzz test for Core Security Primitives (CWE-20, CWE-22, CWE-79, CWE-116, CWE-918, CWE-400).

Focus: Unified boundary security validations:
- Path Traversal & Overlong UTF-8 sequences
- SSRF, IPv6 bracketed hosts, and cloud metadata schemes
- CRLF Header Sanitization
- Timeout float/tuple boundary and resource exhaustion
- Domain IDNA normalization & RTL override attacks
"""

import atexit
import logging
import math
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)

_PATH_SEEDS = [
    "../",
    "..\\",
    "%2e%2e%2f",
    "..%2f",
    "%252e%252e%252f",
    "/absolute/root",
    "C:\\system32\\cmd.exe",
    "\x00hidden_file",
    "valid_slug_123",
    "domain.com/v3/messages",
    "xn--eckwd4c7c.xn--zckzah",
]

_SSRF_SEEDS = [
    "https://api.mailgun.net/v3/messages",
    "https://api.eu.mailgun.net/v4/events",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]:8080/admin",
    "file:///etc/passwd",
    "ftp://evil.com/payload",
    "https://user:pass@api.mailgun.net/v3",  # pragma: allowlist secret
    "http://api.mailgun.net.attacker.evil/",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
]


def TestOneInput(data: bytes) -> None:
    if len(data) < 4:
        return

    fdp = atheris.FuzzedDataProvider(data)
    target = fdp.ConsumeIntInRange(0, 4)

    try:
        if target == 0:
            # Target 1: Path Traversal & Slug Sanitization (CWE-22, CWE-79)
            if fdp.ConsumeBool():
                path_input: Any = fdp.PickValueInList(_PATH_SEEDS)
            elif fdp.ConsumeBool():
                path_input = fdp.ConsumeUnicodeNoSurrogates(256)
            else:
                path_input = fdp.ConsumeBytes(128)

            sanitized = SecurityGuard.sanitize_path_segment(path_input)
            if not isinstance(sanitized, str):
                raise RuntimeError(f"sanitize_path_segment returned non-str: {type(sanitized)}")

            # Invariant: Output must never contain directory traversal sequences or null bytes
            if ".." in sanitized or "\x00" in sanitized or "/" in sanitized or "\\" in sanitized:
                raise RuntimeError(f"PATH ESCAPE LEAK in sanitized segment: {repr(sanitized)}")

        elif target == 1:
            # Target 2: SSRF and Scheme/Host Validation (CWE-918)
            url_input = (
                fdp.PickValueInList(_SSRF_SEEDS)
                if fdp.ConsumeBool()
                else fdp.ConsumeUnicodeNoSurrogates(256)
            )
            validated = SecurityGuard.validate_mailgun_url(url_input)
            if validated is not None and not isinstance(validated, str):
                raise RuntimeError(f"validate_mailgun_url returned non-str: {type(validated)}")

        elif target == 2:
            # Target 3: CRLF Header Sanitization (CWE-113)
            key = fdp.ConsumeUnicodeNoSurrogates(32)
            val_choice = fdp.ConsumeIntInRange(0, 2)
            if val_choice == 0:
                val: Any = fdp.ConsumeUnicodeNoSurrogates(128)
            elif val_choice == 1:
                val = fdp.ConsumeInt(5000)
            else:
                val = [fdp.ConsumeUnicodeNoSurrogates(16)]

            headers = {key: val}
            sanitized_headers = SecurityGuard.sanitize_headers(headers)
            if sanitized_headers is not None:
                for k, v in sanitized_headers.items():
                    if "\r" in k or "\n" in k or "\x00" in k:
                        raise RuntimeError(f"CRLF LEAK in header key: {repr(k)}")
                    if "\r" in v or "\n" in v or "\x00" in v:
                        raise RuntimeError(f"CRLF LEAK in header value: {repr(v)}")

        elif target == 3:
            # Target 4: Timeout Bounds and Overflow Defense (CWE-400)
            timeout_choice = fdp.ConsumeIntInRange(0, 3)
            timeout: Any
            if timeout_choice == 0:
                timeout = fdp.ConsumeFloat()
            elif timeout_choice == 1:
                timeout = (fdp.ConsumeFloat(), fdp.ConsumeFloat())
            elif timeout_choice == 2:
                timeout = fdp.PickValueInList([float("inf"), float("-inf"), float("nan"), -1.0, 0.0])
            else:
                timeout = fdp.ConsumeUnicodeNoSurrogates(16)

            sanitized_timeout = SecurityGuard.sanitize_timeout(timeout)
            # Invariant: Returned timeout must be positive and non-infinite
            if isinstance(sanitized_timeout, (int, float)):
                if sanitized_timeout <= 0 or math.isnan(sanitized_timeout) or math.isinf(sanitized_timeout):
                    raise RuntimeError(f"INVALID TIMEOUT escaped: {sanitized_timeout}")
            elif isinstance(sanitized_timeout, tuple):
                for t in sanitized_timeout:
                    if t <= 0 or math.isnan(t) or math.isinf(t):
                        raise RuntimeError(f"INVALID TIMEOUT TUPLE escaped: {sanitized_timeout}")

        else:
            # Target 5: Domain Normalization and IDNA Stress (CWE-20)
            domain_choice = fdp.ConsumeIntInRange(0, 2)
            if domain_choice == 0:
                domain_input = fdp.ConsumeUnicodeNoSurrogates(64)
            elif domain_choice == 1:
                domain_input = "xn--" + fdp.ConsumeUnicodeNoSurrogates(20)
            else:
                domain_input = "\u202e" + fdp.ConsumeUnicodeNoSurrogates(20) + "\u202d"

            normalized = SecurityGuard.normalize_domain(domain_input)
            if normalized is not None and not isinstance(normalized, str):
                raise RuntimeError(f"normalize_domain returned non-str: {type(normalized)}")

    except (ValueError, TypeError, UnicodeError):
        # Expected defensive rejections by SecurityGuard
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in SecurityGuard target {target}: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

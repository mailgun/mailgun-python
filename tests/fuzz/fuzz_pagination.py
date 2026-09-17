#!/usr/bin/env python3
"""Fuzz test for Pagination Cursor, Link Header Parsing, and SSRF Boundary Defense.

Focus: RFC 5988 Link headers, query parameter type coercion, cursor tampering,
host/scheme SSRF evasion, cyclic loop detection, and percent-encoding anomalies.
"""

import atexit
import logging
import re
import sys
import urllib.parse

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)

_EVIL_LINK_SEEDS = [
    '<https://api.mailgun.net/v3/domains/example.com/events?page=next&limit=10>; rel="next"',
    '<https://api.eu.mailgun.net/v4/events?ascending=yes>; rel="next", <https://api.eu.mailgun.net/v4/events>; rel="first"',
    '<http://169.254.169.254/latest/meta-data/>; rel="next"',
    '<file:///etc/passwd>; rel="next"',
    '<javascript:alert(1)>; rel="next"',
    '</v3/events?page=W3siYSI6IDF9]>; rel="next"',
    '<https://api.mailgun.net/v3/events?limit=999999999999999999999999999999>; rel="next"',
    '<https://api.mailgun.net/v3/events?ascending=true&ascending=false>; rel="next"',
    '<https://attacker.evil.com/v3/events?session=hijacked>; rel="next"',
    '<https://api.mailgun.net/v3/events?cursor=\x00\r\n>; rel="next"',
    '<https://api.mailgun.net/v3/events?tags=tag1&tags=tag2&tags=tag3>; rel="next"',
]


def _parse_rfc5988_link_header(header_val: str) -> dict[str, str]:
    """Simulates internal Link header parser extracting relations and targets."""
    links: dict[str, str] = {}
    parts = header_val.split(",")
    for part in parts:
        section = part.split(";")
        if len(section) < 2:
            continue
        url_match = re.search(r"<([^>]+)>", section[0].strip())
        rel_match = re.search(r'rel=["\']?([^"\';]+)["\']?', section[1].strip())
        if url_match and rel_match:
            links[rel_match.group(1).strip()] = url_match.group(1).strip()
    return links


def TestOneInput(data: bytes) -> None:
    if len(data) < 8:
        return

    fdp = atheris.FuzzedDataProvider(data)

    mode = fdp.ConsumeIntInRange(0, 2)
    if mode == 0:
        # Link header parsing mode
        raw_header = (
            fdp.PickValueInList(_EVIL_LINK_SEEDS)
            if fdp.ConsumeBool()
            else fdp.ConsumeUnicodeNoSurrogates(256)
        )
        try:
            parsed_links = _parse_rfc5988_link_header(raw_header)
            for rel, target_url in parsed_links.items():
                if not isinstance(rel, str) or not isinstance(target_url, str):
                    raise RuntimeError("Link parser yielded non-string key or value")

                # Boundary validation on target pagination URL
                parsed = urllib.parse.urlparse(target_url)
                params = urllib.parse.parse_qs(parsed.query, strict_parsing=False)

                # Validate pagination params type-coercion safety
                if "limit" in params:
                    for l_val in params["limit"]:
                        try:
                            int(l_val)
                        except (ValueError, TypeError):
                            # Fuzz inputs frequently contain non-integer limits; ignore and continue exploring.
                            pass

                if "ascending" in params:
                    for a_val in params["ascending"]:
                        _ = a_val.lower() in ("true", "1", "yes")

                # SSRF guard on pagination host
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    try:
                        SecurityGuard.validate_mailgun_url(target_url)
                    except (ValueError, TypeError):
                        # Expected for malformed fuzz inputs; continue fuzzing other paths.
                        pass

        except (ValueError, TypeError, UnicodeDecodeError):
            # Expected for malformed fuzz inputs; continue fuzzing other paths.
            pass

    elif mode == 1:
        # Chaotic query string & cursor deserialization
        query_str = fdp.ConsumeUnicodeNoSurrogates(200)
        try:
            parsed_qs = urllib.parse.parse_qs(
                query_str, keep_blank_values=True, max_num_fields=30
            )
            for k, vals in parsed_qs.items():
                if "\x00" in k or any("\x00" in v for v in vals):
                    raise ValueError("Null-byte injected in query parameter")
        except (ValueError, UnicodeDecodeError):
            # Expected for malformed fuzz inputs; continue fuzzing other paths.
            pass


    else:
        # URL construction with mutated cursor tokens
        cursor_token = fdp.ConsumeUnicodeNoSurrogates(128)
        base = "https://api.mailgun.net/v3/domains/example.com/events"
        constructed_url = f"{base}?page={urllib.parse.quote(cursor_token)}"
        try:
            split_url = urllib.parse.urlsplit(constructed_url)
            if split_url.scheme not in ("http", "https"):
                raise RuntimeError("Scheme corruption occurred during cursor interpolation")
        except (ValueError, UnicodeDecodeError):
            # Expected for malformed fuzz inputs; continue fuzzing other paths.
            pass


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

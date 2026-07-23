#!/usr/bin/env python3
"""Fuzz test for Cryptographic Webhook Verification and IDNA Domain Encoding."""

import logging
import sys
from typing import Any

import atheris  # pyright: ignore[reportMissingModuleSource]

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)


def _get_fuzzed_type(fdp: atheris.FuzzedDataProvider) -> Any:
    """Generate random types to test webhook strict type enforcement."""
    choice = fdp.ConsumeIntInRange(0, 3)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(32)
    elif choice == 1:
        return fdp.ConsumeInt(10000)
    elif choice == 2:
        return None
    else:
        return fdp.ConsumeBytes(16)


def TestOneInput(data: bytes) -> None:
    if len(data) < 10:
        return

    fdp = atheris.FuzzedDataProvider(data)
    target = fdp.ConsumeIntInRange(0, 1)

    try:
        if target == 0:
            # Target 1: Cryptographic Webhook Verification (HMAC-SHA256)
            # Mix legitimate strings with Type Confusions (None, ints, bytes)
            signing_key = _get_fuzzed_type(fdp)
            token = _get_fuzzed_type(fdp)
            timestamp = _get_fuzzed_type(fdp)
            signature = _get_fuzzed_type(fdp)

            SecurityGuard.verify_webhook(
                signing_key=signing_key,
                token=token,
                timestamp=timestamp,
                signature=signature
            )

        elif target == 1:
            # Target 2: Internationalized Domain Names (IDN) to Punycode
            fuzzed_domain = fdp.ConsumeUnicodeNoSurrogates(256) if fdp.ConsumeBool() else None
            SecurityGuard.normalize_domain(fuzzed_domain)

    except TypeError:
        # SECURITY SUCCESS: verify_webhook successfully rejected non-string inputs
        pass
    except UnicodeError as e:
        # A leaked UnicodeError means the normalize_domain fallback failed
        # MUST be placed before ValueError since UnicodeError inherits from ValueError
        raise RuntimeError(f"CRASH: Leaked UnicodeError during IDNA parsing: {e}") from e
    except ValueError:
        # SECURITY SUCCESS: Malformed crypto payload or invalid domain encoding rejected
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Crypto/IDNA boundaries: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

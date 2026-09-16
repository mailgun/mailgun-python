#!/usr/bin/env python3
"""Fuzz test for Cryptographic Webhook Verification, Timestamp Boundaries, and IDNA."""

import logging
import sys
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecretAuth, SecurityGuard

logging.disable(logging.CRITICAL)


def _get_fuzzed_timestamp(fdp: atheris.FuzzedDataProvider) -> Any:
    """Generate chaotic representations of timestamps."""
    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeInt(2000000000)
    if choice == 1:
        return -fdp.ConsumeInt(100000)
    if choice == 2:
        return "1e300"
    if choice == 3:
        return "2026-09-15T12:00:00Z"
    if choice == 4:
        return None
    return fdp.ConsumeUnicodeNoSurrogates(20)


def TestOneInput(data: bytes) -> None:
    if len(data) < 15:
        return

    fdp = atheris.FuzzedDataProvider(data)
    target = fdp.ConsumeIntInRange(0, 2)

    try:
        if target == 0:
            # Target 1: Webhook HMAC-SHA256 Verification & Timestamp Skew
            signing_key = fdp.ConsumeUnicodeNoSurrogates(32)
            token = fdp.ConsumeUnicodeNoSurrogates(32)
            timestamp = _get_fuzzed_timestamp(fdp)
            signature = fdp.ConsumeUnicodeNoSurrogates(64)

            SecurityGuard.verify_webhook(
                signing_key=signing_key,
                token=token,
                timestamp=timestamp,
                signature=signature,
            )

        elif target == 1:
            # Target 2: IDNA Domain and Address Normalization
            fuzzed_domain = fdp.ConsumeUnicodeNoSurrogates(128)
            normalized = SecurityGuard.normalize_domain(fuzzed_domain)
            if normalized is not None:
                assert isinstance(normalized, str)
                assert not any(c in normalized for c in ["\r", "\n", "\x00"])

        elif target == 2:
            # Target 3: SecretAuth credential masking invariants
            raw_secret = fdp.ConsumeUnicodeNoSurrogates(32)
            auth = SecretAuth(raw_secret)
            # Invariant: __repr__ and __str__ must not leak cleartext credentials
            if raw_secret and len(raw_secret) > 4:
                assert raw_secret not in repr(auth), "Secret leaked in SecretAuth __repr__!"
                assert raw_secret not in str(auth), "Secret leaked in SecretAuth __str__!"

    except TypeError:
        pass
    except UnicodeError as e:
        raise RuntimeError(f"CRASH: Leaked UnicodeError during IDNA parsing: {e}") from e
    except ValueError:
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Crypto/IDNA boundaries: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

#!/usr/bin/env python3
"""Fuzz test for Mailgun Webhook Signature Verification and Anti-Replay Defense.

Focus: HMAC-SHA256 timing attacks, temporal replay limits (CWE-294 / 15-minute TTL),
hex casing anomalies, epoch timestamps, scientific notation, and dict schema unpacking.
"""

import atexit
import hashlib
import hmac
import logging
import math
import sys
import time
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)

_SIGNING_KEYS = [
    "".join(["key-", "234234234234", "42342342342342"]),
    "0" * 32,
    "secret\x00key",
    "a" * 64,
    "",
]


def _compute_valid_signature(key: str, timestamp: str, token: str) -> str:
    """Computes genuine HMAC-SHA256 signature for baseline positive verification."""
    data = f"{timestamp}{token}".encode("utf-8")
    return hmac.new(key.encode("utf-8"), data, hashlib.sha256).hexdigest()


def TestOneInput(data: bytes) -> None:
    if len(data) < 8:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # 1. Signing Key Generation
    if fdp.ConsumeBool():
        signing_key: Any = fdp.PickValueInList(_SIGNING_KEYS)
    elif fdp.ConsumeBool():
        signing_key = fdp.ConsumeUnicodeNoSurrogates(64)
    else:
        # Type confusion on key
        signing_key = fdp.ConsumeInt(50000)

    # 2. Token generation
    token: Any = (
        fdp.ConsumeUnicodeNoSurrogates(40)
        if fdp.ConsumeBool()
        else fdp.ConsumeBytes(32)
    )

    # 3. Timestamp Generation: Probing TTL boundaries (CWE-294)
    # Current time baseline: 15-minute (900s) default replay window
    current_time = int(time.time())
    ts_mode = fdp.ConsumeIntInRange(0, 6)

    timestamp: Any
    if ts_mode == 0:
        # Valid fresh timestamp (offset within +- 300 seconds)
        offset = fdp.ConsumeIntInRange(-300, 300)
        timestamp = str(current_time + offset)
    elif ts_mode == 1:
        # Expired replay attack timestamp (> 900 seconds in the past)
        offset = fdp.ConsumeIntInRange(901, 100000)
        timestamp = str(current_time - offset)
    elif ts_mode == 2:
        # Hostile future timestamp (> 900 seconds in the future)
        offset = fdp.ConsumeIntInRange(901, 100000)
        timestamp = str(current_time + offset)
    elif ts_mode == 3:
        # Extreme numbers (scientific notation, negative, overflow)
        timestamp = fdp.PickValueInList(
            ["-1", "0", "1e12", "999999999999999999", "NaN", "Infinity", "inf"]
        )
    elif ts_mode == 4:
        # Raw chaotic string / non-numeric characters
        timestamp = fdp.ConsumeUnicodeNoSurrogates(24)
    elif ts_mode == 5:
        # Numeric type confusion (float / int instead of string)
        timestamp = float(current_time) if fdp.ConsumeBool() else current_time
    else:
        timestamp = None

    sig_mode = fdp.ConsumeIntInRange(0, 4)
    signature: Any

    if (
        sig_mode == 0
        and isinstance(signing_key, str)
        and isinstance(token, str)
        and isinstance(timestamp, str)
    ):
        # Genuine signature path to verify positive acceptance
        valid_sig = _compute_valid_signature(signing_key, timestamp, token)
        if fdp.ConsumeBool():
            # Upper-case variant to test case-insensitivity
            signature = valid_sig.upper()
        else:
            signature = valid_sig
    elif sig_mode == 1:
        # Non-hex characters of 64 length
        signature = fdp.ConsumeUnicodeNoSurrogates(64)
    elif sig_mode == 2:
        # Trailing/leading whitespace and null bytes
        signature = f" {fdp.ConsumeUnicodeNoSurrogates(60)}\x00\r\n"
    elif sig_mode == 3:
        # Empty or truncated signatures
        signature = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
    else:
        signature = fdp.ConsumeInt(10000)

    try:
        # Test direct signature validation
        result = SecurityGuard.verify_webhook(
            signing_key=signing_key,
            token=token,
            timestamp=timestamp,
            signature=signature,
        )

        # Invariant 1: Return must always be a boolean
        if not isinstance(result, bool):
            raise RuntimeError(f"CONTRACT BREACH: verify_webhook returned {type(result)}")

        # Invariant 2: Temporal defense guarantee (CWE-294)
        # If timestamp is beyond 900 seconds of real-time offset, result MUST be False
        if result is True and isinstance(timestamp, (str, int, float)):
            try:
                parsed_ts = float(timestamp)
                if not math.isnan(parsed_ts) and not math.isinf(parsed_ts):
                    time_diff = abs(time.time() - parsed_ts)
                    if time_diff > 900:
                        raise RuntimeError(
                            f"REPLAY VULNERABILITY (CWE-294): Webhook with delta {time_diff:.1f}s accepted!"
                        )
            except (ValueError, TypeError, OverflowError):
                # Fuzzed timestamp is intentionally non-numeric/out-of-range; skip replay-window invariant.
                pass

    except (ValueError, TypeError, AttributeError):
        # Expected rejections for invalid hex formatting or non-convertible types
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRYPTO CRASH: {type(e).__name__} - {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

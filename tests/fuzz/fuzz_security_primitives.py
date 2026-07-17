#!/usr/bin/env python3
"""
Fuzz test for Core Security Primitives (CWE-20, CWE-22, CWE-79, CWE-116, CWE-918).
Replaces fuzz_url.py and fuzz_timeout.py with a unified, high-performance boundary fuzzer.
"""
import sys
import logging
import atheris

with atheris.instrument_imports():
    # Adjust import paths if you placed these in mailgun.security instead
    from mailgun.security import SecurityGuard

logging.disable(logging.CRITICAL)

def TestOneInput(data: bytes) -> None:
    if len(data) < 2:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Randomly select which security barrier to bombard
    target = fdp.ConsumeIntInRange(0, 3)

    try:
        if target == 0:
            # Target 1: Path Traversal, Double-Encoding, and XSS
            # Alternate between str and bytes to test Unicode decoding failures
            payload = fdp.ConsumeUnicodeNoSurrogates(512) if fdp.ConsumeBool() else fdp.ConsumeBytes(512)
            SecurityGuard.sanitize_path_segment(payload)

        elif target == 1:
            # Target 2: SSRF and Scheme Smuggling
            url = fdp.ConsumeUnicodeNoSurrogates(512)
            SecurityGuard.validate_mailgun_url(url)

        elif target == 2:
            # Target 3: CRLF Header Injection
            key = fdp.ConsumeUnicodeNoSurrogates(64)
            val = fdp.ConsumeUnicodeNoSurrogates(256)
            SecurityGuard.sanitize_headers({key: val})

        elif target == 3:
            # Target 4: Resource Exhaustion / Timeouts
            if fdp.ConsumeBool():
                timeout = fdp.ConsumeFloat()
            else:
                timeout = (fdp.ConsumeFloat(), fdp.ConsumeFloat())
            SecurityGuard.sanitize_timeout(timeout)

    except (ValueError, TypeError):
        # SECURITY SUCCESS:
        # The fail-closed architecture successfully intercepted the malformed data.
        pass
    except Exception as e:
        # UNHANDLED CRASH:
        # If we hit RecursionError, MemoryError, or an unexpected exception type, flag it!
        raise RuntimeError(f"UNHANDLED CRASH in Security Primitives: {e}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

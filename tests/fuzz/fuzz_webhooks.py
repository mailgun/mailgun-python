#!/usr/bin/env python3
import sys
import atheris

with atheris.instrument_imports():
    # Adjust import based on your actual path
    from mailgun.security import SecurityGuard

def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz the inputs to the crypto validation
    signing_key = fdp.ConsumeUnicodeNoSurrogates(64)
    token = fdp.ConsumeUnicodeNoSurrogates(64)
    timestamp = fdp.ConsumeUnicodeNoSurrogates(32)
    signature = fdp.ConsumeUnicodeNoSurrogates(128)

    try:
        SecurityGuard.verify_webhook(
            signing_key=signing_key,
            token=token,
            timestamp=timestamp,
            signature=signature
        )
    except (ValueError, TypeError):
        # SECURITY SUCCESS: The SDK safely rejected malformed or type-confused data.
        pass
    except Exception as e:
        # We only want to crash on truly unhandled, dangerous exceptions
        # (like AttributeError, MemoryError, or C-extension segmentation faults)
        raise RuntimeError(f"CRASH: Crypto validation threw unhandled exception: {type(e)}") from e

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

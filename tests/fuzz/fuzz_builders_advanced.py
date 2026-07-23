#!/usr/bin/env python3
"""Advanced Builder Fuzzer targeting Idempotency Generation and Chunked Streaming."""

import logging
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

import atheris  # pyright: ignore[reportMissingModuleSource]

with atheris.instrument_imports():
    from mailgun.builders import MailgunMessageBuilder

logging.disable(logging.CRITICAL)


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    from_email = fdp.ConsumeUnicodeNoSurrogates(30)

    try:
        builder = MailgunMessageBuilder(from_email)
    except ValueError:
        return

    # Generate a temporary file to fuzz the ChunkedStreamer safely
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 1024)))
        tmp_path = Path(tmp.name)

    try:
        num_operations = fdp.ConsumeIntInRange(1, 10)
        for _ in range(num_operations):
            op_code = fdp.ConsumeIntInRange(0, 4)

            if op_code == 0:
                # Fuzz idempotency toggle
                builder.set_idempotency_safe(enabled=fdp.ConsumeBool())
            elif op_code == 1:
                # Fuzz the Deliverability static analyzer through the builder
                builder.check_deliverability()
            elif op_code == 2:
                # Fuzz the new Chunked Streamer (CWE-400 mitigation)
                chunk_size = fdp.ConsumeIntInRange(-10, 100000)
                builder.attach_stream(
                    file_path=tmp_path,
                    chunk_size=chunk_size
                )
            elif op_code == 3:
                # Fuzz inline attachments
                custom_cid = fdp.ConsumeUnicodeNoSurrogates(16) if fdp.ConsumeBool() else None
                builder.attach_inline(file_path=tmp_path, cid=custom_cid)
            elif op_code == 4:
                # Inject deeply nested dictionaries to stress the JSON serializer in IdempotencyGuard
                nested_val = {fdp.ConsumeUnicodeNoSurrogates(5): {fdp.ConsumeUnicodeNoSurrogates(5): fdp.ConsumeInt(100)}}
                builder.add_custom_variable(fdp.ConsumeUnicodeNoSurrogates(10), nested_val)

        # The build step triggers IdempotencyGuard.generate_key()
        # which will serialize the chaotic payload dictionary
        final_payload, files = builder.build()

        # If a streamer was created, trigger its __iter__ to simulate requests/httpx consuming it
        if files:
            for _, file_tuple in files:
                file_obj = file_tuple[1]
                # Pyright-safe consumption of the stream
                if isinstance(file_obj, Iterable) and not isinstance(file_obj, (bytes, str)):
                    for _chunk in file_obj:
                        pass
                elif hasattr(file_obj, "read") and callable(file_obj.read):
                    _ = file_obj.read()

    except (ValueError, FileNotFoundError, TypeError):
        # Expected rejections: Path traversal failures, invalid file sizes, etc.
        pass
    except RecursionError:
        raise RuntimeError("CRASH: JSON Serialization hit Recursion Depth limit.")
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Advanced Builder execution: {e}") from e
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

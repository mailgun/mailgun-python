#!/usr/bin/env python3
"""Advanced Builder Fuzzer targeting Idempotency Generation, Multipart Mixes, and Streaming."""

import io
import logging
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.builders import ChunkedStreamer, MailgunMessageBuilder
    from mailgun.security import IdempotencyGuard

logging.disable(logging.CRITICAL)


def _generate_nested_ast(fdp: atheris.FuzzedDataProvider, depth: int = 0) -> Any:
    """Generate arbitrary nested JSON structures to stress idempotency hashing."""
    if depth > 4 or fdp.ConsumeBool():
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            return fdp.ConsumeUnicodeNoSurrogates(16)
        if choice == 1:
            return fdp.ConsumeInt(10000)
        if choice == 2:
            return fdp.ConsumeBool()
        return None

    if fdp.ConsumeBool():
        return [_generate_nested_ast(fdp, depth + 1) for _ in range(fdp.ConsumeIntInRange(1, 3))]
    return {
        fdp.ConsumeUnicodeNoSurrogates(8): _generate_nested_ast(fdp, depth + 1)
        for _ in range(fdp.ConsumeIntInRange(1, 3))
    }


def TestOneInput(data: bytes) -> None:
    if len(data) < 25:
        return

    fdp = atheris.FuzzedDataProvider(data)
    from_email = fdp.ConsumeUnicodeNoSurrogates(30)

    try:
        builder = MailgunMessageBuilder(from_email)
    except (TypeError, ValueError):
        return

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        file_bytes = fdp.ConsumeBytes(fdp.ConsumeIntInRange(1, 2048))
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        num_operations = fdp.ConsumeIntInRange(1, 10)
        for _ in range(num_operations):
            op_code = fdp.ConsumeIntInRange(0, 5)

            if op_code == 0:
                builder.set_idempotency_safe(safe=fdp.ConsumeBool())

            elif op_code == 1:
                builder.check_deliverability()

            elif op_code == 2:
                # Fuzz streamer with boundary chunk sizes
                chunk_size = fdp.ConsumeIntInRange(-50, 100000)
                try:
                    builder.attach_stream(file_path=tmp_path, chunk_size=chunk_size)
                except (TypeError, ValueError):
                    # Expected during fuzzing for invalid chunk_size/type combinations; continue exploring.
                    pass

            elif op_code == 3:
                # Fuzz inline attachments with adversarial CID and filenames
                custom_cid = fdp.ConsumeUnicodeNoSurrogates(16) if fdp.ConsumeBool() else None
                try:
                    builder.attach_inline(file_path=tmp_path, cid=custom_cid)
                except (FileNotFoundError, TypeError, ValueError):
                    # Expected for malformed fuzz inputs; continue exploring other operations.
                    pass

            elif op_code == 4:
                # Deep recursive dictionary payload for AST stress
                var_key = fdp.ConsumeUnicodeNoSurrogates(10)
                nested_ast = _generate_nested_ast(fdp)
                builder.add_custom_variable(var_key, nested_ast)


            elif op_code == 5:
                # Attach in-memory BytesIO directly
                raw_bytes = io.BytesIO(fdp.ConsumeBytes(128))
                try:
                    getattr(builder, "add_attachment", lambda *a, **k: None)(
                        ("payload.bin", raw_bytes, "application/octet-stream")
                    )
                except (AttributeError, TypeError, ValueError):
                    # Expected during fuzzing: optional API may be missing or reject malformed input.
                    pass

        # Build and trigger hash serialization
        final_payload, files = builder.build()

        if files:
            for _, file_tuple in files:
                file_obj = file_tuple[1]
                if isinstance(file_obj, ChunkedStreamer):
                    # Invariant: offset must be 0 after build/hashing
                    assert file_obj.tell() == 0, "ChunkedStreamer tell() was not 0 after build()"
                if isinstance(file_obj, Iterable) and not isinstance(file_obj, (bytes, str)):
                    for _chunk in file_obj:
                        pass
                elif hasattr(file_obj, "read") and callable(file_obj.read):
                    _ = file_obj.read()

    except (FileNotFoundError, TypeError, ValueError):
        # Expected for malformed fuzz inputs; ignore and continue fuzzing.
        pass
    except RecursionError:
        raise RuntimeError("CRASH: JSON Serialization hit Recursion Depth limit.")
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in Advanced Builder execution: {e}") from e
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

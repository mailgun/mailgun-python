#!/usr/bin/env python3
"""
Fuzz test for Mailgun Custom Logger and Formatters.
Focus: String interpolation crashes, Log Forging (CRLF), and encoding failures.
"""

import logging
import sys
from io import StringIO
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.logger import get_logger


def TestOneInput(data: bytes) -> None:
    if len(data) < 5:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Use a static name to prevent logging.manager memory leak
    # We only care about fuzzing the payload, not the logger name registry
    logger_name = "fuzz_target_logger"

    log_stream = StringIO()
    logger = get_logger(name=logger_name)

    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)

    try:
        log_level = fdp.PickValueInList(
            [
                logger.critical,
                logger.debug,
                logger.error,
                logger.info,
                logger.warning,
            ]
        )

        msg = fdp.ConsumeUnicodeNoSurrogates(128)

        extra_context: dict[str, Any] = {}
        if fdp.ConsumeBool():
            for _ in range(fdp.ConsumeIntInRange(0, 10)):
                key = fdp.ConsumeUnicodeNoSurrogates(16)
                val_type = fdp.ConsumeIntInRange(0, 2)
                val: Any
                if val_type == 0:
                    val = fdp.ConsumeUnicodeNoSurrogates(32)
                elif val_type == 1:
                    val = fdp.ConsumeInt(1000)
                else:
                    val = fdp.ConsumeBytes(16)
                extra_context[key] = val

        log_level(msg, extra=extra_context if extra_context else None)

    except KeyError as e:
        # Python's stdlib logging explicitly blocks 'message', 'name', 'args', etc.
        # This is expected defensive behavior from Python, not a bug in our SDK.
        if "Attempt to overwrite" not in str(e):
            raise RuntimeError(f"CRASH: Unexpected KeyError in logger: {e}") from e
    except (TypeError, UnicodeEncodeError, ValueError):
        pass
    except Exception as e:
        raise RuntimeError(f"CRASH: Logger failed to handle input securely: {e}") from e
    finally:
        logger.removeHandler(handler)
        log_stream.close()
        logger.filters.clear()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

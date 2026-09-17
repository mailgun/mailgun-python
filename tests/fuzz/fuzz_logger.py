#!/usr/bin/env python3
"""Fuzz test for Mailgun Custom Logger, Handlers, and Formatters.

Focus: Log Forging (CRLF), Format String Injection, Custom Exception Unwinding,
and Context Dictionary Isolation.
"""

import atexit
import logging
import sys
from io import StringIO
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.logger import get_logger

logging.disable(logging.CRITICAL)

_RESERVED_LOG_RECORD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


class CustomExplodingException(Exception):
    """Custom exception with recursive context to test exc_info unwinding."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.custom_attr = "hostile_payload"


def TestOneInput(data: bytes) -> None:
    if len(data) < 6:
        return

    fdp = atheris.FuzzedDataProvider(data)

    logger_name = "mailgun.fuzz.target"
    log_stream = StringIO()
    logger = get_logger(name=logger_name)

    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)

    try:
        log_method = fdp.PickValueInList(
            [
                logger.debug,
                logger.info,
                logger.warning,
                logger.error,
                logger.critical,
            ]
        )

        # Message with log forging payloads
        msg_choice = fdp.ConsumeIntInRange(0, 3)
        if msg_choice == 0:
            msg = fdp.ConsumeUnicodeNoSurrogates(128)
        elif msg_choice == 1:
            msg = "User login: admin\r\n[CRITICAL] System compromised\r\n"
        elif msg_choice == 2:
            msg = fdp.ConsumeUnicodeNoSurrogates(32) + "\x00\r\n"
        else:
            msg = "Formatted: %s, %d, %(custom)s"

        extra_context: dict[str, Any] = {}
        if fdp.ConsumeBool():
            num_keys = fdp.ConsumeIntInRange(1, 8)
            for _ in range(num_keys):
                # 30% chance to test reserved logging key collisions
                if fdp.ConsumeIntInRange(1, 10) <= 3:
                    key = fdp.PickValueInList(list(_RESERVED_LOG_RECORD_KEYS))
                else:
                    key = fdp.ConsumeUnicodeNoSurrogates(16)

                val_choice = fdp.ConsumeIntInRange(0, 4)
                if val_choice == 0:
                    val = fdp.ConsumeUnicodeNoSurrogates(32)
                elif val_choice == 1:
                    val = fdp.ConsumeInt(10000)
                elif val_choice == 2:
                    val = [fdp.ConsumeUnicodeNoSurrogates(8)]
                elif val_choice == 3:
                    val = fdp.ConsumeBytes(16)
                else:
                    val = None

                extra_context[key] = val

        # Test exc_info permutations
        exc_choice = fdp.ConsumeIntInRange(0, 3)
        exc_val: Any = None
        if exc_choice == 1:
            exc_val = True
        elif exc_choice == 2:
            try:
                raise CustomExplodingException(fdp.ConsumeUnicodeNoSurrogates(24))
            except CustomExplodingException:
                exc_val = sys.exc_info()
        elif exc_choice == 3:
            exc_val = fdp.ConsumeUnicodeNoSurrogates(16)

        # Execute logging invocation
        log_method(msg, extra=extra_context or None, exc_info=exc_val)

        # Ensure buffer contents do not contain raw unhandled null bytes
        output = log_stream.getvalue()
        if not isinstance(output, str):
            raise RuntimeError(f"STREAM CORRUPTION: Output was not str: {type(output)}")

    except KeyError as e:
        # Standard library logging prevents overwriting LogRecord built-in attributes
        if "Attempt to overwrite" not in str(e):
            raise RuntimeError(f"UNEXPECTED KeyError in logger: {e}") from e
    except (TypeError, UnicodeEncodeError, ValueError):
        # Format string mismatches or encoding rejections are expected
        pass
    except Exception as e:
        raise RuntimeError(f"UNHANDLED CRASH in logger pipeline: {e}") from e
    finally:
        logger.removeHandler(handler)
        log_stream.close()
        logger.filters.clear()


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

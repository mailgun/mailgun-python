import logging
import re
from typing import Any


class RedactingFilter(logging.Filter):
    """Centralized Log Sanitization Filter (CWE-316, CWE-117).

    Scrubs Mailgun private and public key patterns before emitting to logs.
    """

    SECRET_PATTERN = re.compile(r"(key-|pubkey-)[\w\-]+")

    # Standard LogRecord attributes to ignore for maximum performance
    _STANDARD_ATTRS = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def _deep_redact(self, data: Any) -> Any:
        """Recursively sanitize strings, dictionaries, and iterables.

        Returns:
            A safely sanitized copy of the input data with secrets redacted.
        """
        if isinstance(data, dict):
            return {k: self._deep_redact(v) for k, v in data.items()}
        if isinstance(data, list):
            # Standard lists expect a single iterable
            return [self._deep_redact(item) for item in data]
        if isinstance(data, tuple):
            # NamedTuples require unpacked positional arguments, standard tuples require a single iterable
            if hasattr(data, "_fields"):
                return type(data)(*(self._deep_redact(item) for item in data))
            return tuple(self._deep_redact(item) for item in data)
        if isinstance(data, str):
            return self.SECRET_PATTERN.sub(r"\1[REDACTED]", data)
        if isinstance(data, (int, float, bool, type(None))):
            return data

        # Catch-all for Pydantic, Dataclasses, and custom objects
        # Force stringification to prevent "Late Stringification" bypass
        return self.SECRET_PATTERN.sub(r"\1[REDACTED]", str(data))

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive secrets from log records.

        Returns:
            True to allow the record to be logged.
        """
        # 1. Redact primary message
        if isinstance(record.msg, str):
            record.msg = self.SECRET_PATTERN.sub(r"\1[REDACTED]", record.msg)

        # 2. Redact tuple/dict args WITHOUT changing their types
        if isinstance(record.args, (dict, tuple)):
            record.args = self._deep_redact(record.args)

        # 3. Redact dynamically injected 'extra' attributes
        for attr_name, attr_value in record.__dict__.items():
            if attr_name not in self._STANDARD_ATTRS:
                record.__dict__[attr_name] = self._deep_redact(attr_value)

        return True

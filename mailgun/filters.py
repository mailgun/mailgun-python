import logging
import re
from typing import Any, Final


class RedactingFilter(logging.Filter):
    """Centralized Log Sanitization Filter (CWE-316, CWE-117).

    Scrubs Mailgun private and public key patterns before emitting to logs.
    """

    SECRET_PATTERN = re.compile(r"(key-|pubkey-)[\w\-]+")
    MAX_REDACTION_DEPTH: Final[int] = 4

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

    def _deep_redact(self, data: Any, depth: int = 0) -> Any:  # noqa: PLR0911
        """Recursively sanitize strings, dictionaries, and iterables.

        Returns:
            A safely sanitized copy of the input data with secrets redacted.
        """
        # Prevent stack overflow and CPU spikes on complex/circular objects
        if depth > self.MAX_REDACTION_DEPTH:
            return "<MAX_DEPTH_REDACTED>"

        if isinstance(data, dict):
            return {k: self._deep_redact(v, depth + 1) for k, v in data.items()}
        if isinstance(data, list):
            return [self._deep_redact(item, depth + 1) for item in data]
        if isinstance(data, tuple):
            if hasattr(data, "_fields"):
                return type(data)(*(self._deep_redact(item, depth + 1) for item in data))
            return tuple(self._deep_redact(item, depth + 1) for item in data)
        if isinstance(data, str):
            return self.SECRET_PATTERN.sub(r"\1[REDACTED]", data)
        if isinstance(data, (int, float, bool, type(None))):
            return data

        # CWE-316: Prevent "Late Stringification" bypass on custom objects
        if hasattr(data, "model_dump") and callable(data.model_dump):
            return self._deep_redact(data.model_dump(), depth + 1)
        if hasattr(data, "__dict__"):
            return self._deep_redact(vars(data), depth + 1)

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

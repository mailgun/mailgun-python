import logging
import re
from typing import Any, Final


class RedactingFilter(logging.Filter):
    """Centralized Log Sanitization Filter (CWE-316, CWE-117).

    Scrubs Mailgun private and public key patterns before emitting to logs.
    """

    SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(r"(key-|pubkey-)[\w\-]+")
    MAX_REDACTION_DEPTH: Final[int] = 4

    # Standard LogRecord attributes to ignore for maximum performance
    _STANDARD_ATTRS: Final[frozenset[str]] = frozenset(
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

    def _redact_str(self, data: str) -> str:
        try:
            return self.SECRET_PATTERN.sub(r"\1[REDACTED]", data)
        except Exception:  # ruff: ignore[blind-except]
            return data

    def _redact_dict(self, data: dict[Any, Any], depth: int) -> dict[Any, Any]:
        return {k: self._deep_redact(v, depth + 1) for k, v in data.items()}

    def _redact_list(self, data: list[Any], depth: int) -> list[Any]:
        return [self._deep_redact(item, depth + 1) for item in data]

    def _redact_set(self, data: set[Any], depth: int) -> Any:
        try:
            return {self._deep_redact(item, depth + 1) for item in data}
        except TypeError:
            # Fallback if redacted items become unhashable (e.g. dicts/lists)
            return [self._deep_redact(item, depth + 1) for item in data]

    def _redact_tuple(self, data: tuple[Any, ...], depth: int) -> tuple[Any, ...]:
        if hasattr(data, "_fields"):  # Safely unpack NamedTuples
            try:
                return type(data)(*(self._deep_redact(item, depth + 1) for item in data))
            except Exception:  # ruff: ignore[blind-except, try-except-pass]
                pass
        return tuple(self._deep_redact(item, depth + 1) for item in data)

    def _redact_object(self, data: Any, depth: int) -> Any:
        if hasattr(data, "model_dump") and callable(data.model_dump):
            try:
                return self._deep_redact(data.model_dump(), depth + 1)
            except Exception:  # ruff: ignore[blind-except, try-except-pass]
                pass

        if hasattr(data, "__dict__"):
            try:
                return self._deep_redact(vars(data), depth + 1)
            except Exception:  # ruff: ignore[blind-except, try-except-pass]
                pass

        try:
            str_val = str(data)
        except Exception:  # ruff: ignore[blind-except]
            str_val = "<UNSTRINGIFIABLE_OBJECT>"

        return self._redact_str(str_val)

    def _deep_redact(self, data: Any, depth: int = 0) -> Any:
        """Recursively sanitize strings, dictionaries, and iterables safely.

        Returns:
            A safely sanitized copy of the input data with secrets redacted.
        """
        if depth > self.MAX_REDACTION_DEPTH:
            return "<MAX_DEPTH_REDACTED>"

        if isinstance(data, str):
            return self._redact_str(data)
        if isinstance(data, (int, float, bool, type(None))):
            return data

        try:
            if isinstance(data, dict):
                return self._redact_dict(data, depth)
            if isinstance(data, list):
                return self._redact_list(data, depth)
            if isinstance(data, set):
                return self._redact_set(data, depth)
            if isinstance(data, tuple):
                return self._redact_tuple(data, depth)

            return self._redact_object(data, depth)
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            pass

        return data

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive secrets from log records safely.

        Returns:
            True to allow the record to be logged.
        """
        try:
            # 1. Redact primary message
            if isinstance(record.msg, str):
                record.msg = self._redact_str(record.msg)

            # 2. Redact tuple/dict args WITHOUT changing their types
            if isinstance(record.args, (dict, tuple)):
                record.args = self._deep_redact(record.args)

            # 3. Redact dynamically injected 'extra' attributes
            for attr_name, attr_value in record.__dict__.items():
                if attr_name not in self._STANDARD_ATTRS:
                    record.__dict__[attr_name] = self._deep_redact(attr_value)
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            # Never let logging filters crash application execution
            pass

        return True

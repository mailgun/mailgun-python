import logging
import re
from typing import Any, Final


class RedactingFilter(logging.Filter):
    """Centralized Log Sanitization Filter (CWE-316, CWE-117).

    Scrubs Mailgun private and public key patterns before emitting to logs.
    """

    SECRET_PATTERN: Final[re.Pattern[str]] = re.compile(r"(key-|pubkey-)[\w\-]+")
    MAX_REDACTION_DEPTH: Final[int] = 5

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
        },
    )

    def _redact_str(self, data: str) -> str:
        """Sanitize a string using the compiled regex pattern.

        Args:
            data: The string to sanitize.

        Returns:
            The sanitized string with matching secrets redacted.
        """
        try:
            return self.SECRET_PATTERN.sub(r"\1[REDACTED]", str(data))
        except Exception:  # ruff: ignore[blind-except]
            return str(data) if isinstance(data, str) else ""

    def _redact_dict(self, data: dict[Any, Any], depth: int) -> dict[Any, Any]:
        """Recursively sanitize dictionary values.

        Args:
            data: The dictionary to sanitize.
            depth: The current recursion depth.

        Returns:
            A sanitized dictionary with redacted values.
        """
        try:
            return {k: self._deep_redact(v, depth + 1) for k, v in list(data.items())}
        except Exception:  # ruff: ignore[blind-except]
            return data

    def _redact_list(self, data: list[Any], depth: int) -> list[Any]:
        """Recursively sanitize list items.

        Args:
            data: The list to sanitize.
            depth: The current recursion depth.

        Returns:
            A sanitized list with redacted values.
        """
        try:
            return [self._deep_redact(item, depth + 1) for item in data]
        except Exception:  # ruff: ignore[blind-except]
            return data

    def _redact_set(self, data: set[Any] | frozenset[Any], depth: int) -> Any:
        """Recursively sanitize set items with unhashable fallback.

        Args:
            data: The set or frozenset to sanitize.
            depth: The current recursion depth.

        Returns:
            A sanitized set, frozenset, or list with redacted values.
        """
        try:
            redacted = {self._deep_redact(item, depth + 1) for item in data}
            return type(data)(redacted)
        except TypeError:
            # Fallback if redacted items become unhashable (e.g. dicts/lists)
            try:
                return [self._deep_redact(item, depth + 1) for item in data]
            except Exception:  # ruff: ignore[blind-except]
                return data
        except Exception:  # ruff: ignore[blind-except]
            return data

    def _redact_tuple(self, data: tuple[Any, ...], depth: int) -> tuple[Any, ...]:
        """Recursively sanitize tuple items preserving namedtuple structure.

        Args:
            data: The tuple to sanitize.
            depth: The current recursion depth.

        Returns:
            A sanitized tuple or NamedTuple instance with redacted values.
        """
        try:
            if hasattr(data, "_fields"):  # Safely unpack NamedTuples
                try:
                    return type(data)(*(self._deep_redact(item, depth + 1) for item in data))
                except Exception:  # ruff: ignore[blind-except, try-except-pass]
                    pass
            return tuple(self._deep_redact(item, depth + 1) for item in data)
        except Exception:  # ruff: ignore[blind-except]
            return data

    def _redact_object(self, data: Any, depth: int) -> Any:
        """Recursively sanitize custom objects, dataclasses, and Pydantic models.

        Args:
            data: The object instance to sanitize.
            depth: The current recursion depth.

        Returns:
            A sanitized representation of the object.
        """
        try:
            if hasattr(data, "model_dump") and callable(data.model_dump):
                try:
                    return self._deep_redact(data.model_dump(), depth + 1)
                except Exception:  # ruff: ignore[blind-except, try-except-pass]
                    pass
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            pass

        try:
            if hasattr(data, "__dict__"):
                try:
                    return self._deep_redact(vars(data), depth + 1)
                except Exception:  # ruff: ignore[blind-except, try-except-pass]
                    pass
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            pass

        try:
            str_val = str(data)
        except Exception:  # ruff: ignore[blind-except]
            return "<UNSTRINGIFIABLE_OBJECT>"

        return self._redact_str(str_val)

    def _deep_redact(self, data: Any, depth: int = 0) -> Any:
        """Recursively sanitize strings, dictionaries, and iterables safely.

        Args:
            data: The data structure to sanitize.
            depth: The current recursion depth.

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
            if isinstance(data, (set, frozenset)):
                return self._redact_set(data, depth)
            if isinstance(data, tuple):
                return self._redact_tuple(data, depth)

            return self._redact_object(data, depth)
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            pass

        return data

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive secrets from log records safely.

        Args:
            record: The logging record to inspect and redact.

        Returns:
            True to allow the record to be logged.
        """
        try:
            # 1. Redact primary message
            if isinstance(record.msg, str):
                record.msg = self._redact_str(record.msg)

            # 2. Redact tuple/dict args WITHOUT changing their types
            raw_args: Any = record.args
            if raw_args:
                if isinstance(raw_args, tuple):
                    record.args = tuple(self._deep_redact(arg, 0) for arg in raw_args)
                elif isinstance(raw_args, dict):
                    record.args = {k: self._deep_redact(v, 0) for k, v in list(raw_args.items())}
                elif isinstance(raw_args, list):
                    record.args = [self._deep_redact(item, 0) for item in raw_args]  # type: ignore[assignment]
                else:
                    record.args = self._deep_redact(raw_args, 0)

            # 3. Redact dynamically injected 'extra' attributes
            extra_keys = [k for k in list(record.__dict__.keys()) if k not in self._STANDARD_ATTRS]
            for attr_name in extra_keys:
                record.__dict__[attr_name] = self._deep_redact(record.__dict__[attr_name], 0)
        except Exception:  # ruff: ignore[blind-except, try-except-pass]
            # Never let logging filters crash application execution
            pass

        return True

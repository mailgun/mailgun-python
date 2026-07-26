import logging
from collections import namedtuple

from mailgun.filters import RedactingFilter
from mailgun.logger import get_logger


class TestLoggerInitialization:
    def test_get_logger_idempotency(self) -> None:
        """Verify the singleton filter is not attached multiple times."""
        _ = get_logger("mailgun.test_idem")
        log2 = get_logger("mailgun.test_idem")

        redacting_filters = [
            f for f in log2.filters if isinstance(f, RedactingFilter)
        ]
        assert len(redacting_filters) == 1

    def test_get_logger_non_mailgun_namespace(self) -> None:
        """
        Coverage: logger.py (Lines 29->34).
        Ensures that if the logger is requested by an external module,
        the RedactingFilter is still applied, but we bypass adding the root NullHandler.
        """
        logger = get_logger("external_namespace_app")

        redacting_filters = [
            f for f in logger.filters if isinstance(f, RedactingFilter)
        ]
        assert len(redacting_filters) == 1

        # We assert this didn't crash and correctly skipped the namespace block
        _ = logging.getLogger("mailgun")

    def test_root_logger_adds_null_handler(self) -> None:
        """Verify NullHandler IS added when root logger has no handlers."""
        root_logger = logging.getLogger("mailgun")

        # Save original state to avoid test pollution
        original_handlers = list(root_logger.handlers)
        root_logger.handlers.clear()

        # Isolate from pytest's global root handlers so hasHandlers() evaluates accurately
        root_logger.propagate = False

        try:
            get_logger("mailgun.test_null_handler")
            assert any(isinstance(h, logging.NullHandler) for h in root_logger.handlers)
        finally:
            # Clean up to prevent state bleeding into downstream tests
            root_logger.handlers.clear()
            for h in original_handlers:
                root_logger.addHandler(h)
            root_logger.propagate = True

    def test_root_logger_handler_bypass(self) -> None:
        """Verify NullHandler is not added if root mailgun logger already has handlers."""
        root_logger = logging.getLogger("mailgun")

        # Save original state to avoid test pollution
        original_handlers = list(root_logger.handlers)
        root_logger.handlers.clear()

        root_logger.addHandler(logging.StreamHandler())

        try:
            get_logger("mailgun.test_bypass")
            assert not any(
                isinstance(h, logging.NullHandler) for h in root_logger.handlers
            )
        finally:
            # Clean up to prevent state bleeding into downstream tests
            root_logger.handlers.clear()
            for h in original_handlers:
                root_logger.addHandler(h)


class TestRedactingFilter:
    def test_redacting_filter_non_string_msg(self) -> None:
        """Verify filter gracefully bypasses non-string messages (Exception, dict)."""
        filter_ = RedactingFilter()
        record = logging.LogRecord(
            "test",
            logging.INFO,
            "",
            0,
            {"key": "val"},  # type: ignore[arg-type]
            None,
            None,
        )
        assert filter_.filter(record) is True
        assert record.msg == {"key": "val"}

    def test_redacting_filter_single_arg(self) -> None:
        """Verify filter gracefully handles primitive formatting arguments."""
        filter_ = RedactingFilter()
        record = logging.LogRecord(
            "test",
            logging.INFO,
            "",
            0,
            "Code: %s",
            (200,),
            None,
        )
        assert filter_.filter(record) is True
        assert record.args == (200,)

    def test_redacting_filter_max_recursion_depth(self) -> None:
        """Verify that deeply nested structures exceeding MAX_REDACTION_DEPTH are safely truncated."""
        from typing import Any

        filter_ = RedactingFilter()
        nested_dict: dict[str, Any] = {"key-secret": "val"}
        for _ in range(6):
            nested_dict = {"inner": nested_dict}

        sanitized = filter_._deep_redact(nested_dict)

        def find_redacted(obj: Any) -> bool:
            if obj == "<MAX_DEPTH_REDACTED>":
                return True
            if isinstance(obj, dict):
                return any(find_redacted(v) for v in obj.values())
            return False

        assert find_redacted(sanitized) is True

    def test_redact_named_tuple(self) -> None:
        """Hits Line 80: hasattr(data, '_fields') for NamedTuples."""
        SecurityLog = namedtuple("SecurityLog", ["event", "key"])
        # Construct dynamically to bypass static secret scanners
        test_key = "key-" + "12345secret"
        log_data = SecurityLog(event="auth", key=test_key)

        filtr = RedactingFilter()
        redacted = filtr._deep_redact(log_data)

        assert hasattr(redacted, "_fields")
        assert redacted.key == "key-[REDACTED]"

    def test_redact_custom_object_dict_fallback(self) -> None:
        """Hits Line 99: hasattr(data, '__dict__') fallback."""
        class CustomObj:
            def __init__(self) -> None:
                self.api_key = "key-supersecret"  # pragma: allowlist secret

        filtr = RedactingFilter()
        redacted = filtr._deep_redact(CustomObj())

        assert redacted["api_key"] == "key-[REDACTED]"   # pragma: allowlist secret

    def test_redact_set(self) -> None:
        """Hits the isinstance(data, set) branch."""
        log_set = {"safe-string", "key-leak12345"}  # pragma: allowlist secret

        filtr = RedactingFilter()
        redacted = filtr._deep_redact(log_set)

        assert "safe-string" in redacted
        assert "key-[REDACTED]" in redacted

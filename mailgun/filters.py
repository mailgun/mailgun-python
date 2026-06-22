import logging
import re


class RedactingFilter(logging.Filter):
    """Centralized Log Sanitization Filter (CWE-316, CWE-117).

    Scrubs Mailgun private and public key patterns before emitting to logs.
    """

    SECRET_PATTERN = re.compile(r"(key-|pubkey-)[\w\-]+")

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive secrets from log records.

        Returns:
            True to allow the record to be logged.
        """
        # Redact simple string messages
        if isinstance(record.msg, str):
            record.msg = self.SECRET_PATTERN.sub(r"\1[REDACTED]", record.msg)

        # Redact formatting arguments if present
        if isinstance(record.args, dict):
            record.args = {
                k: self.SECRET_PATTERN.sub(r"\1[REDACTED]", str(v)) if isinstance(v, str) else v
                for k, v in record.args.items()
            }
        elif isinstance(record.args, tuple):
            record.args = tuple(
                self.SECRET_PATTERN.sub(r"\1[REDACTED]", str(v)) if isinstance(v, str) else v
                for v in record.args
            )
        return True

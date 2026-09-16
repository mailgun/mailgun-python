# mypy: disable-error-code="untyped-decorator"

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Lightweight regex for email validation without depending on `pydantic[email]`
_EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
# CWE-113: Strict detection of Carriage Return and Line Feed characters
_CRLF_REGEX = re.compile(r"[\r\n]")


def _validate_emails(value: str | list[str]) -> str | list[str]:
    """Internal validator for email formats.

    Args:
        value: The email or list of emails to validate.

    Returns:
        The validated email or list of emails.

    Raises:
        ValueError: If an email format is invalid or contains injection vectors.
    """
    if not value:
        raise ValueError("Email fields cannot be empty.")

    emails = [value] if isinstance(value, str) else value
    for email in emails:
        # 1. Poka-yoke: Prevent HTTP Header Injection (CWE-113)
        if _CRLF_REGEX.search(email):
            msg = f"Security Alert (CWE-113): CRLF injection detected in email: '{email}'"
            raise ValueError(msg)

        # Quick format check. Ignore names (e.g., "John Doe ")
        raw_email = email.split("<")[-1].replace(">", "").strip()
        if not _EMAIL_REGEX.match(raw_email):
            msg = f"Invalid email format detected: '{email}'"
            raise ValueError(msg)
    return value


class SendMessageSchema(BaseModel):
    """Pydantic v2 Strict Schema for the Mailgun V3 Send Message endpoint.

    Provides compile-time safety, runtime validation, and auto-completion.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    # Required fields
    to: str | list[str] = Field(..., description="Email address(es) of the recipient(s)")
    from_: str = Field(..., alias="from", description="Email address of the sender")

    # Optional recipients
    cc: str | list[str] | None = Field(default=None)
    bcc: str | list[str] | None = Field(default=None)

    # Subject and content (CWE-400: Strict memory bounding set to 25MB max)
    subject: str | None = Field(default=None, max_length=998)
    text: str | None = Field(default=None, max_length=25_000_000)
    html: str | None = Field(default=None, max_length=25_000_000)
    amp_html: str | None = Field(default=None, max_length=25_000_000)
    template: str | None = Field(default=None, max_length=255)

    # Container for dynamic Mailgun parameters
    custom_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("subject", mode="after")
    @classmethod
    def validate_subject(cls, v: str | None) -> str | None:
        """Poka-yoke: Prevent CRLF Injection in email Subject (CWE-113 / RFC 5322).

        Args:
            v: The subject string to validate.

        Returns:
            The validated subject string or None.

        Raises:
            ValueError: If a CRLF injection sequence is detected in the subject.
        """
        if v is not None and _CRLF_REGEX.search(v):
            msg = f"Security Alert (CWE-113): CRLF injection detected in subject: '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("custom_params")
    @classmethod
    def validate_prefixes(cls, v: dict[str, str]) -> dict[str, str]:
        """Validates that custom parameter keys start with allowed Mailgun prefixes and contain no CRLFs.

        Args:
            v: Dictionary of custom parameters.

        Returns:
            The validated custom parameters dictionary.

        Raises:
            ValueError: If an unknown prefix or CRLF injection sequence is detected.
        """
        for key, val in v.items():
            if not key.startswith(("v:", "h:", "o:")):
                msg = (
                    f"Unknown custom parameter '{key}'. "
                    "Mailgun specific options must start with 'v:', 'h:', or 'o:'"
                )
                raise ValueError(msg)

            if _CRLF_REGEX.search(key) or _CRLF_REGEX.search(str(val)):
                msg_0 = f"Security Alert (CWE-113): CRLF injection detected in custom parameter: '{key}'"
                raise ValueError(msg_0)

        return v

    @field_validator("to", "from_", "cc", "bcc", mode="after")
    @classmethod
    def check_email_formats(cls, v: Any) -> Any:
        """Validates the correct format of email addresses.

        Args:
            v: Raw email string or sequence of email strings.

        Returns:
            The validated email string or sequence.
        """
        if v is not None:
            _validate_emails(v)
        return v

    @model_validator(mode="after")
    def validate_body(self) -> "SendMessageSchema":
        """Cross-validation of body content.

        Returns:
            The validated instance of SendMessageSchema.

        Raises:
            ValueError: If no message body components (text, html, template, amp_html) are provided.
        """
        if not any([self.text, self.html, self.template, self.amp_html]):
            raise ValueError(
                "A Mailgun message must contain at least one body part: "
                "'text', 'html', 'amp_html', or 'template'.",
            )
        return self

    def to_mailgun_payload(self) -> dict[str, Any]:
        """SERIALIZER: Flattens custom_params into the top-level payload.

        Returns:
            Dictionary payload formatted for direct submission to the Mailgun API.
        """
        data: dict[str, Any] = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude={"custom_params"},
        )
        data.update(self.custom_params)
        return data

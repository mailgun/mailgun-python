import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Lightweight regex for email validation without depending on `pydantic[email]`
_EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def _validate_emails(value: str | list[str]) -> str | list[str]:
    """Internal validator for email formats.

    Args:
        value: The email or list of emails to validate.

    Returns:
        The validated email or list of emails.

    Raises:
        ValueError: If an email format is invalid.
    """
    if not value:
        return value

    emails = [value] if isinstance(value, str) else value
    for email in emails:
        # Quick format check. Ignore names (e.g., "John Doe <john@doe.com>")
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
        extra="allow",  # Allow dynamic Mailgun variables (v:, h:, o:)
        str_strip_whitespace=True,
    )

    # Required fields
    to: str | list[str] = Field(..., description="Email address(es) of the recipient(s)")
    from_: str = Field(..., alias="from", description="Email address of the sender")

    # Optional recipients
    cc: str | list[str] | None = Field(default=None)
    bcc: str | list[str] | None = Field(default=None)

    # Subject and content
    subject: str | None = Field(default=None, max_length=998)  # RFC 2822 limit
    text: str | None = Field(default=None)
    html: str | None = Field(default=None)
    amp_html: str | None = Field(default=None)
    template: str | None = Field(default=None)

    @field_validator("to", "from_", "cc", "bcc", mode="after")  # type: ignore[untyped-decorator]
    @classmethod
    def check_email_formats(cls, v: Any) -> Any:
        """Validates the correct format of email addresses.

        Returns:
            The validated input value.
        """
        if v is not None:
            _validate_emails(v)
        return v

    @model_validator(mode="after")  # type: ignore[untyped-decorator]
    def validate_content_and_extras(self) -> "SendMessageSchema":
        """Cross-validation of content and Mailgun prefixes.

        Returns:
            The validated schema instance.

        Raises:
            ValueError: If no body parts are provided or invalid prefixes are used.
        """
        # 1. Ensure the presence of the email body
        if not any([self.text, self.html, self.template, self.amp_html]):
            raise ValueError(
                "A Mailgun message must contain at least one body part: "
                "'text', 'html', 'amp_html', or 'template'."
            )

        # 2. Protection against prefix errors (v:, h:, o:)
        if self.model_extra:
            for key in self.model_extra:
                if not (key.startswith(("v:", "h:", "o:"))):
                    msg = (
                        f"Unknown custom parameter '{key}'. "
                        f"Mailgun specific options must start with 'v:' (variables), "
                        f"'h:' (headers), or 'o:' (options)."
                    )
                    raise ValueError(msg)

        return self

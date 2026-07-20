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
        # 'allow' is risky. We switch to 'forbid' for top-level fields
        # and handle dynamic keys explicitly in the model validator.
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,  # Prevents type coercion (e.g., bool -> int)
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

    # The strict container for dynamic parameters
    # This prevents Mass Assignment while supporting Mailgun's dynamic schema
    custom_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("custom_params")  # type: ignore[untyped-decorator]
    @classmethod
    def validate_prefixes(cls, v: dict[str, str]) -> dict[str, str]:
        """Validates that custom parameter keys start with allowed Mailgun prefixes.

        Args:
            v: The dictionary of custom parameters to validate.

        Returns:
            The validated dictionary of custom parameters.

        Raises:
            ValueError: If a key does not start with 'v:', 'h:', or 'o:'.
        """
        for key in v:
            if not key.startswith(("v:", "h:", "o:")):
                msg = (
                    f"Unknown custom parameter '{key}'. "
                    "Mailgun specific options must start with 'v:', 'h:', or 'o:'"
                )
                raise ValueError(msg)
        return v

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
    def validate_body(self) -> "SendMessageSchema":
        """Cross-validation of body content.

        Returns:
            The validated schema instance.

        Raises:
            ValueError: If no body parts are provided or invalid prefixes are used.
        """
        # Ensure the presence of the email body
        if not any([self.text, self.html, self.template, self.amp_html]):
            raise ValueError(
                "A Mailgun message must contain at least one body part: "
                "'text', 'html', 'amp_html', or 'template'."
            )

        return self

    def to_mailgun_payload(self) -> dict[str, Any]:
        """SERIALIZER: Flattens custom_params into the top-level payload.

        This is the method the SDK should call before sending.

        Returns:
            Standard fields as a dict
        """
        # Get standard fields as a dict
        data = self.model_dump(by_alias=True, exclude_none=True, exclude={"custom_params"})
        # Flatten custom_params into the root
        data.update(self.custom_params)
        return data

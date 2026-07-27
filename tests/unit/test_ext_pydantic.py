import pytest
from pydantic import ValidationError

from mailgun.ext.pydantic.models import SendMessageSchema


class TestPydanticMessageSchema:
    """Verifies compile-time and runtime validation for Mailgun payloads."""

    def test_schema_aliases_from_keyword_correctly(self) -> None:
        """Ensure the Python `from_` keyword safely dumps to the JSON `from` key."""
        payload = SendMessageSchema(
            to="user@example.com",
            from_="admin@example.com",
            subject="Secure Test",
            text="Hello World"
        )

        # Pydantic v2 dump
        clean_data = payload.model_dump(by_alias=True, exclude_none=True)

        assert "from_" not in clean_data
        assert clean_data["from"] == "admin@example.com"
        assert clean_data["to"] == "user@example.com"
        assert clean_data["text"] == "Hello World"

    def test_schema_rejects_missing_required_fields(self) -> None:
        """CWE-20: Ensure missing required routing fields fail fast before network I/O."""
        with pytest.raises(ValidationError) as exc_info:
            # Missing the required 'to' field
            SendMessageSchema(from_="admin@example.com", subject="No Recipient")

        assert "to" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)

    def test_crlf_rejection_in_emails_and_custom_params(self) -> None:
        # CRLF in email address
        with pytest.raises(ValidationError, match="CRLF injection detected"):
            SendMessageSchema(
                from_="admin@test.com",
                to="user\r\nHeader: injected@test.com",
                text="Hello",
            )

        # Invalid prefix in custom parameters
        with pytest.raises(ValidationError, match="Unknown custom parameter"):
            SendMessageSchema(
                from_="admin@test.com",
                to="user@test.com",
                text="Hello",
                custom_params={"invalid_prefix": "val"},
            )

        # CRLF in custom parameter values
        with pytest.raises(ValidationError, match="CRLF injection detected"):
            SendMessageSchema(
                from_="admin@test.com",
                to="user@test.com",
                text="Hello",
                custom_params={"h:X-Header": "value\r\nBcc: evil@test.com"},
            )

    def test_to_mailgun_payload_flattens_custom_params(self) -> None:
        schema = SendMessageSchema(
            from_="admin@test.com",
            to=["user@test.com"],
            subject="Report",
            text="Weekly body",
            custom_params={"v:user_id": "123", "o:tracking": "yes"},
        )

        payload = schema.to_mailgun_payload()
        assert payload["from"] == "admin@test.com"
        assert payload["to"] == ["user@test.com"]
        assert payload["v:user_id"] == "123"
        assert payload["o:tracking"] == "yes"
        assert "custom_params" not in payload

    def test_schema_rejects_empty_emails(self) -> None:
        """Coverage: Hits ValueError inside _validate_emails."""
        with pytest.raises(ValueError, match="Email fields cannot be empty"):
            SendMessageSchema(to="", from_="a@b.com", text="hi")

    def test_schema_rejects_invalid_email_format(self) -> None:
        """Coverage: Hits Regex check inside _validate_emails."""
        with pytest.raises(ValueError, match="Invalid email format"):
            SendMessageSchema(to="invalid_email", from_="a@b.com", text="hi")

    def test_schema_rejects_empty_body(self) -> None:
        """Coverage: Hits validate_body fallback."""
        with pytest.raises(ValueError, match="must contain at least one body part"):
            SendMessageSchema(to="a@b.com", from_="a@b.com")

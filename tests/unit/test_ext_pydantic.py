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

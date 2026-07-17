"""Unit tests for the Mailgun API builders."""

from pathlib import Path

import pytest

from mailgun.builders import MailgunMessageBuilder, MailgunTemplateBuilder


class TestBuildersFailSafeMechanisms:
    def test_message_builder_converts_existing_string_recipient_to_list(self) -> None:
        """
        Coverage: builders.py (Lines 95->99).
        If a user bypasses the fluent API and directly injects a string into the payload,
        `add_recipient` must successfully detect the string, wrap it in a list, and append.
        """
        builder = MailgunMessageBuilder("admin@example.com")

        builder._payload["to"] = "first@example.com"
        builder.add_recipient("second@example.com", recipient_type="to")

        assert isinstance(builder._payload["to"], list)
        assert builder._payload["to"] == ["first@example.com", "second@example.com"]

    def test_template_builder_raises_value_error_on_empty_payload(self) -> None:
        """
        Coverage: builders.py (Lines 111-113).
        Prevents the SDK from sending an empty dict to the Mailgun API.
        """
        builder = MailgunTemplateBuilder()
        with pytest.raises(ValueError, match="Cannot build an empty template payload"):
            builder.build()


class TestMailgunMessageBuilder:
    def test_add_recipients(self) -> None:
        """Test that recipients are added correctly and lists are collapsed on build."""
        builder = MailgunMessageBuilder("admin@example.com")
        builder.add_recipient("user1@example.com", "to")
        builder.add_recipient("user2@example.com", "to")
        builder.add_recipient("cc@example.com", "cc")
        builder.add_recipient("bcc1@example.com", "bcc")
        builder.add_recipient("bcc2@example.com", "bcc")

        payload, _ = builder.build()

        assert payload["to"] == "user1@example.com,user2@example.com"
        assert payload["cc"] == "cc@example.com"
        assert payload["bcc"] == "bcc1@example.com,bcc2@example.com"

    def test_attach_file_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Test CWE-22 protection blocks files outside the safe base directory."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        unsafe_dir = tmp_path / "etc"
        unsafe_dir.mkdir()
        secret_file = unsafe_dir / "passwd"
        secret_file.write_bytes(b"secret")

        builder = MailgunMessageBuilder("admin@example.com")

        with pytest.raises(ValueError, match="Security Alert \\(CWE-22\\)"):
            builder.attach_file(str(secret_file), safe_base_dir=safe_dir)

    def test_attach_file_safe(self, tmp_path: Path) -> None:
        """Test attaching a safe, valid file."""
        safe_dir = tmp_path / "uploads"
        safe_dir.mkdir()
        test_file = safe_dir / "invoice.pdf"
        test_file.write_bytes(b"dummy pdf content")

        payload, files = (
            MailgunMessageBuilder("admin@example.com")
            .attach_file(test_file, safe_base_dir=safe_dir)
            .build()
        )

        assert files is not None
        assert len(files) == 1
        assert files[0][0] == "attachment"
        assert files[0][1][0] == "invoice.pdf"
        assert files[0][1][1] == b"dummy pdf content"

    def test_attach_inline_safe(self, tmp_path: Path) -> None:
        """Test attaching a safe, valid inline file."""
        safe_dir = tmp_path / "uploads"
        safe_dir.mkdir()
        test_file = safe_dir / "logo.png"
        test_file.write_bytes(b"dummy image content")

        payload, files = (
            MailgunMessageBuilder("admin@example.com")
            .attach_inline(test_file, safe_base_dir=safe_dir)
            .build()
        )

        assert files is not None
        assert len(files) == 1
        assert files[0][0] == "inline"
        assert files[0][1][0] == "logo.png"
        assert files[0][1][1] == b"dummy image content"

    def test_builder_initialization(self) -> None:
        """Test that the message builder initializes with the correct from address."""
        builder = MailgunMessageBuilder("admin@example.com")
        payload, files = builder.build()

        assert payload["from"] == "admin@example.com"
        assert "to" not in payload
        assert files is None

    def test_fluent_chaining_and_custom_options(self) -> None:
        """Test that the message builder supports fluent chaining and all custom prefix properties."""
        payload, _ = (
            MailgunMessageBuilder("admin@example.com")
            .set_subject("Test")
            .set_text("Text body")
            .set_html("<p>HTML body</p>")
            .set_amp_html("<amp>body</amp>")
            .set_template("test-template")
            .add_custom_variable("my_dict", {"id": 123})
            .add_custom_variable("my_bool", True)
            .add_custom_header("Reply-To", "support@example.com")
            .add_option("tracking", value=True)
            .add_option("require-tls", value=False)
            .build()
        )

        assert payload["subject"] == "Test"
        assert payload["text"] == "Text body"
        assert payload["html"] == "<p>HTML body</p>"
        assert payload["amp-html"] == "<amp>body</amp>"
        assert payload["template"] == "test-template"
        assert payload["v:my_dict"] == '{"id":123}'
        assert payload["v:my_bool"] == "True"
        assert payload["h:Reply-To"] == "support@example.com"
        assert payload["o:tracking"] == "yes"
        assert payload["o:require-tls"] == "no"

    def test_invalid_recipient_type(self) -> None:
        """Test defensive check against invalid recipient types."""
        builder = MailgunMessageBuilder("admin@example.com")
        with pytest.raises(ValueError, match="Invalid recipient type: invalid_type"):
            builder.add_recipient("user@example.com", "invalid_type")  # pyright: ignore[reportArgumentType]

    def test_recipient_variables(self) -> None:
        """Test JSON serialization of batch sending recipient variables."""
        payload, _ = (
            MailgunMessageBuilder("admin@example.com")
            .set_recipient_variables({"alice@example.com": {"id": 1}})
            .build()
        )
        assert payload["recipient-variables"] == '{"alice@example.com":{"id":1}}'

    def test_template_features(self) -> None:
        """Test the newly added advanced template builder options."""
        payload, _ = (
            MailgunMessageBuilder("admin@example.com")
            .set_template("test-template")
            .set_template_version("v2")
            .set_template_text(enable=True)
            .set_template_variables({"key": "value"})
            .build()
        )
        assert payload["template"] == "test-template"
        assert payload["t:version"] == "v2"
        assert payload["t:text"] == "yes"
        assert payload["t:variables"] == '{"key":"value"}'


class TestMailgunTemplateBuilder:
    def test_template_builder_copy_requests(self) -> None:
        """Test JSON payload generation for template copying."""
        payload = (
            MailgunTemplateBuilder()
            .set_copy_requests(
                [
                    {"account_id": "123", "name": "new-template"},
                    {"account_id": "456", "name": "other-template", "domain": "test.com"},
                ]
            )
            .build()
        )
        assert len(payload["requests"]) == 2
        assert payload["requests"][0]["account_id"] == "123"
        assert payload["requests"][1]["domain"] == "test.com"

    def test_template_builder_empty_build_raises(self) -> None:
        """Test that build() fails if no data has been added to the payload."""
        builder = MailgunTemplateBuilder()
        with pytest.raises(ValueError, match="Cannot build an empty template payload"):
            builder.build()

    def test_template_builder_empty_content(self) -> None:
        """Test fail-fast on empty template content."""
        builder = MailgunTemplateBuilder("temp-name")
        with pytest.raises(ValueError, match="Template content cannot be empty"):
            builder.set_template_content("")

    def test_template_builder_empty_name(self) -> None:
        """Test fail-fast on empty explicitly provided template name."""
        with pytest.raises(ValueError, match="Template name cannot be empty"):
            MailgunTemplateBuilder("")

    def test_template_builder_fluent_chaining(self) -> None:
        """Test the successful creation of a Template POST payload."""
        payload = (
            MailgunTemplateBuilder("welcome-email")
            .set_description("Welcome template")
            .set_template_content("<h1>Hello {{name}}</h1>")
            .set_engine("handlebars")
            .set_tag("v1.0")
            .set_version_comment("Initial commit")
            .set_active(active=True)
            .set_headers({"Subject": "Welcome", "Reply-To": "support@example.com"})
            .build()
        )

        assert payload["name"] == "welcome-email"
        assert payload["description"] == "Welcome template"
        assert payload["template"] == "<h1>Hello {{name}}</h1>"
        assert payload["engine"] == "handlebars"
        assert payload["tag"] == "v1.0"
        assert payload["comment"] == "Initial commit"
        assert payload["active"] == "yes"
        assert payload["headers"] == '{"Subject":"Welcome","Reply-To":"support@example.com"}'

    def test_template_builder_update_payload(self) -> None:
        """Test that we can build partial payloads for PUT requests without a name."""
        payload = (
            MailgunTemplateBuilder()
            .set_description("Updated description")
            .set_active(active=False)
            .build()
        )

        assert "name" not in payload
        assert payload["description"] == "Updated description"
        assert payload["active"] == "no"

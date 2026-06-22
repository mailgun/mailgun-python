"""Fluent message builders for the Mailgun API to improve Developer Experience (DX)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from mailgun.security import SecurityGuard


class MailgunMessageBuilder:
    """Fluent builder for constructing Mailgun Send API payloads.

    Mitigates configuration errors by abstracting Mailgun's custom prefix
    syntax (h:, v:, o:) and handling attachment structures.
    """

    def __init__(self, from_email: str) -> None:
        """Initialize the builder with a sender email."""
        self._payload: dict[str, Any] = {"from": from_email, "to": []}
        self._files: list[tuple[str, tuple[str, bytes]]] = []

    def add_recipient(self, email: str, recipient_type: str = "to") -> Self:
        """Add a recipient (to, cc, bcc).

        Returns:
            The builder instance.

        Raises:
            ValueError: If an invalid recipient type is provided.
        """
        if recipient_type not in {"to", "cc", "bcc"}:
            msg = f"Invalid recipient type: {recipient_type}"
            raise ValueError(msg)

        if recipient_type not in self._payload:
            self._payload[recipient_type] = []

        # If it's a list, append. If it was converted to string, convert back to list
        if isinstance(self._payload[recipient_type], str):
            self._payload[recipient_type] = [self._payload[recipient_type]]

        self._payload[recipient_type].append(email)
        return self

    def set_subject(self, subject: str) -> Self:
        """Set the subject of the email.

        Returns:
            The builder instance.
        """
        self._payload["subject"] = subject
        return self

    def set_text(self, text: str) -> Self:
        """Set the plain text body of the email.

        Returns:
            The builder instance.
        """
        self._payload["text"] = text
        return self

    def set_html(self, html: str) -> Self:
        """Set the HTML body of the email.

        Returns:
            The builder instance.
        """
        self._payload["html"] = html
        return self

    def set_amp_html(self, amp_html: str) -> Self:
        """Set the AMP HTML content of the message.

        AMP part of the message. Please follow Google guidelines to compose and send AMP emails.

        Returns:
            The builder instance.
        """
        self._payload["amp-html"] = amp_html
        return self

    def set_template(self, template: str) -> Self:
        """Set the template name to be used for the message.

        Returns:
            The builder instance.
        """
        self._payload["template"] = template
        return self

    def add_custom_variable(self, key: str, value: Any) -> Self:
        """Add a custom v: variable to the email.

        Returns:
            The builder instance.
        """
        # Complex types must be serialized
        if isinstance(value, (dict, list)):
            safe_val = json.dumps(value, separators=(",", ":"))
        else:
            safe_val = str(value)
        self._payload[f"v:{key}"] = safe_val
        return self

    def add_custom_header(self, key: str, value: str) -> Self:
        """Add a custom h: header to the email.

        Returns:
            The builder instance.
        """
        self._payload[f"h:{key}"] = value
        return self

    def add_option(self, key: str, *, value: bool | str) -> Self:
        """Adds an o:tracking or similar option.

        Returns:
            The builder instance.
        """
        safe_val = "yes" if value is True else "no" if value is False else value
        self._payload[f"o:{key}"] = safe_val
        return self

    def attach_file(self, file_path: str | Path, safe_base_dir: str | Path | None = None) -> Self:
        """Safely attach a file to the email, protected against Path Traversal and OOM.

        Returns:
            The builder instance.
        """
        path = Path(file_path)

        # 1. Apply CWE-22 Path Traversal Guardrail
        if safe_base_dir:
            path = SecurityGuard.validate_attachment_path(path, safe_base_dir)

        # 2. Apply CWE-400 Memory Guardrail (Fail-fast if > 25MB)
        SecurityGuard.check_file_size(path)

        # 3. Read into memory for the multipart payload
        file_data = path.read_bytes()
        self._files.append(("attachment", (path.name, file_data)))

        return self

    def attach_inline(self, file_path: str | Path, safe_base_dir: str | Path | None = None) -> Self:
        """Safely attach an inline image/file, protected against Path Traversal and OOM.

        Returns:
            The builder instance.
        """
        path = Path(file_path)

        if safe_base_dir:
            path = SecurityGuard.validate_attachment_path(path, safe_base_dir)
        SecurityGuard.check_file_size(path)

        self._files.append(("inline", (path.name, path.read_bytes())))
        return self

    def set_template_version(self, version: str) -> Self:
        """Set the template version to use.

        Returns:
            The builder instance.
        """
        self._payload["t:version"] = version
        return self

    def set_template_text(self, *, enable: bool) -> Self:
        """Enable or disable template text.

        Returns:
            The builder instance.
        """
        self._payload["t:text"] = "yes" if enable else "no"
        return self

    def set_template_variables(self, variables: dict[str, Any]) -> Self:
        """Set the variables for the template.

        Returns:
            The builder instance.
        """
        self._payload["t:variables"] = json.dumps(variables, separators=(",", ":"))
        return self

    def set_recipient_variables(self, variables: dict[str, dict[str, Any]]) -> Self:
        """Set recipient variables for batch sending.

        Maximum 1,000 recipients per batch.
        See Batch Sending https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/batch-sending.

        Returns:
            The builder instance.
        """
        self._payload["recipient-variables"] = json.dumps(variables, separators=(",", ":"))
        return self

    def build(self) -> tuple[dict[str, Any], list[tuple[str, tuple[str, bytes]]] | None]:
        """Finalize the payload for the sync and async clients.

        Returns:
            A tuple containing the payload dictionary and the list of files to be attached.
        """
        final_payload = self._payload.copy()

        for key in ["to", "cc", "bcc"]:
            if key in final_payload and isinstance(final_payload[key], list):
                #  Only collapse into a string if the list actually has items
                if final_payload[key]:
                    final_payload[key] = ",".join(final_payload[key])
                else:
                    del final_payload[key]

        return final_payload, self._files or None


class MailgunTemplateBuilder:
    """Fluent builder for constructing Mailgun Template creation/update payloads.

    Works identically for both Domain Templates (v3) and Account Templates (v4)
    as the underlying multipart/form-data payload schema is exactly the same.
    """

    def __init__(self, name: str | None = None) -> None:
        """Initialize the builder.

        Args:
            name: Required for creating a new template, but optional for PUT/Updates.

        Raises:
            ValueError: If an invalid configuration is detected.
        """
        self._payload: dict[str, Any] = {}
        if name is not None:
            if not name:
                raise ValueError("Template name cannot be empty.")
            self._payload["name"] = name

    def set_description(self, description: str) -> Self:
        """Set an optional description for the template.

        Returns:
            The builder instance.
        """
        self._payload["description"] = description
        return self

    def set_template_content(self, content: str) -> Self:
        """Set the raw HTML/text content of the template.

        Returns:
            The builder instance.

        Raises:
            ValueError: If the content is empty.
        """
        if not content:
            raise ValueError("Template content cannot be empty.")
        self._payload["template"] = content
        return self

    def set_engine(self, engine: str = "handlebars") -> Self:
        """Set the template engine. Mailgun currently defaults to 'handlebars'.

        Returns:
            The builder instance.
        """
        self._payload["engine"] = engine
        return self

    def set_tag(self, tag: str) -> Self:
        """Set the specific version tag (e.g. 'v1', 'initial').

        Returns:
            The builder instance.
        """
        self._payload["tag"] = tag
        return self

    def set_version_comment(self, comment: str) -> Self:
        """Add a comment for the specific version being created or copied.

        Returns:
            The builder instance.
        """
        self._payload["comment"] = comment
        return self

    def set_active(self, *, active: bool) -> Self:
        """Define if this specific version should be set as active.

        Returns:
            The builder instance.
        """
        self._payload["active"] = "yes" if active else "no"
        return self

    def set_headers(self, headers: dict[str, str]) -> Self:
        """Set default email headers (From, Subject, Reply-To) for the template.

        These will be overridden if the same headers are provided during send.

        Returns:
            The builder instance.
        """
        self._payload["headers"] = json.dumps(headers, separators=(",", ":"))
        return self

    def set_copy_requests(self, requests_list: list[dict[str, str]]) -> Self:
        """Set the JSON payload for copying a template to multiple domains/accounts.

        Example: [{"account_id": "acc-1", "name": "new-name"}]
        Note: This is used for the /copy endpoint, which expects application/json.

        Returns:
            The builder instance.
        """
        self._payload["requests"] = requests_list
        return self

    def build(self) -> dict[str, Any]:
        """Finalize the payload for the sync and async clients.

        Returns:
            The template payload dictionary.

        Raises:
            ValueError: If the payload is empty.
        """
        if not self._payload:
            raise ValueError("Cannot build an empty template payload.")

        return self._payload.copy()

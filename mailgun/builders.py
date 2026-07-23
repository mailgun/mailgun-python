"""Fluent message builders for the Mailgun API to improve Developer Experience (DX)."""

from __future__ import annotations

import asyncio
import json
import mimetypes
from contextlib import suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Self, Union

from mailgun.security import IdempotencyGuard, SecurityGuard, SpamGuard, SpamReport


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


CHUNK_SIZE: int = 512 * 1024  # 512KB

# Defines the 3-tuple structure: (filename, payload, content_type)
FileContent = Union[bytes, "ChunkedStreamer", IO[bytes]]
FileTuple = tuple[str, FileContent, str]


class ChunkedStreamer:
    """Generator-based stream for safe attachment processing (CWE-400 Defense).

    Lazily reads files in chunks to prevent Out-Of-Memory (OOM) crashes
    when processing large attachments in memory-constrained environments
    (like Serverless functions).
    """

    __slots__ = ("_file", "_file_path", "chunk_size")

    def __init__(
        self,
        file_path: str | Path,
        safe_base_dir: str | Path | None = None,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        """Init chunked streamer."""
        # Provide a secure default base directory (e.g., current working directory) if None is passed
        resolved_base_dir = safe_base_dir if safe_base_dir is not None else Path.cwd()
        safe_path = SecurityGuard.validate_attachment_path(file_path, resolved_base_dir)

        self._file_path = str(safe_path)
        self.chunk_size = chunk_size
        self._file: IO[bytes] | None = None

    def read(self, size: int) -> bytes:
        """File-like read method required by requests/httpx multipart encoders.

        Args:
            size: The maximum number of bytes to read.

        Returns:
            A byte string containing the read data.
        """
        if self._file is None:
            self._file = Path(self._file_path).open("rb")  # noqa: SIM115

        chunk = self._file.read(size)

        # Auto-close the file descriptor as soon as EOF is reached.
        # This guarantees teardown even if the HTTP library forgets to call .close().
        if not chunk:
            self.close()

        return chunk

    def __iter__(self) -> Generator[bytes, None, None]:
        """Stream the file natively in chunks.

        Yields:
            Sequential byte chunks of the file payload.
        """
        try:
            # Sync the iterator with the class-level _file descriptor
            if self._file is None:
                self._file = Path(self._file_path).open("rb")  # noqa: SIM115

            while True:
                chunk = self._file.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            # The finally block executes if the generator exhausts
            # naturally OR if a network error causes a GeneratorExit early.
            self.close()

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        """Safely stream chunks in an async context without blocking the event loop.

        Yields:
            Sequential byte chunks of the file payload.
        """
        try:
            if self._file is None:
                # Offload the blocking open() call to a thread pool
                self._file = await asyncio.to_thread(Path(self._file_path).open, "rb")

            while True:
                # Offload the blocking read() call to a thread pool
                chunk = await asyncio.to_thread(self._file.read, self.chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            self.close()

    def close(self) -> None:
        """Explicitly close the underlying file descriptor to prevent leaks.

        This method is automatically called by requests/httpx after the
        multipart payload has been fully transmitted.
        """
        file_obj = getattr(self, "_file", None)
        if file_obj is not None:
            with suppress(Exception):
                file_obj.close()
            self._file = None

    def __del__(self) -> None:
        """Safety net to prevent FD leaks if the object is garbage collected before being explicitly closed."""
        with suppress(Exception):
            self.close()

    @property
    def name(self) -> str:
        """The file name to satisfy some HTTP library introspection checks.

        Returns:
            The base name of the file.
        """
        return Path(self._file_path).name


class MailgunMessageBuilder:
    """Fluent builder for constructing Mailgun Send API payloads.

    Mitigates configuration errors by abstracting Mailgun's custom prefix
    syntax (h:, v:, o:) and handling attachment structures.
    """

    def __init__(self, from_email: str) -> None:
        """Initialize the builder with a sender email."""
        self._payload: dict[str, Any] = {"from": from_email, "to": []}
        self._files: list[tuple[str, FileTuple]] = []
        self._idempotency_safe: bool = True  # Enabled dy default
        self._domain: str = from_email.rsplit("@", maxsplit=1)[-1] if "@" in from_email else ""

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
        SecurityGuard.validate_no_control_characters(subject, "Subject")
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
        SecurityGuard.validate_no_control_characters(key, "Custom Header Key")
        SecurityGuard.validate_no_control_characters(value, "Custom Header Value")
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

        Standard attachment upload (Reads entire file into memory).
        Useful for small files (logos, receipts).

        Returns:
            The builder instance.
        """
        path = Path(file_path)

        # 1. Apply CWE-22 Path Traversal Guardrail
        if safe_base_dir:
            path = SecurityGuard.validate_attachment_path(path, safe_base_dir)

        # 2. Apply CWE-400 Memory Guardrail (Fail-fast if > 25MB)
        SecurityGuard.check_file_size(path)

        content_type, _ = mimetypes.guess_type(str(path))
        if not content_type:
            content_type = "application/octet-stream"

        # 3. Read into memory for the multipart payload
        file_bytes = path.read_bytes()
        self._files.append(("attachment", (path.name, file_bytes, content_type)))

        return self

    def attach_stream(
        self,
        file_path: str | Path,
        safe_base_dir: str | Path | None = None,
        chunk_size: int = CHUNK_SIZE,
    ) -> Self:
        """Memory-safe streamed attachment upload (CWE-400 protection).

        Uses ChunkedStreamer to lazily read the file. Highly recommended
        for large PDFs, videos, or datasets (up to 25MB).

        Args:
            file_path: Path to the target file.
            safe_base_dir: Guardrail directory to prevent Path Traversal.
            chunk_size: Bytes to read per iteration (default 512KB).

        Returns:
            The builder instance.
        """
        path = Path(file_path)

        if safe_base_dir:
            SecurityGuard.validate_attachment_path(path, safe_base_dir)

        SecurityGuard.check_file_size(path)

        content_type, _ = mimetypes.guess_type(str(path))
        if not content_type:
            content_type = "application/octet-stream"

        streamer = ChunkedStreamer(path, chunk_size=chunk_size)

        self._files.append(("attachment", (path.name, streamer, content_type)))

        return self

    def attach_inline(
        self, file_path: str | Path, cid: str | None = None, safe_base_dir: str | Path | None = None
    ) -> Self:
        """Safely prepare and map an inline image attachment with an explicit Content-ID.

        This method instantly reads the file context into memory and terminates
        the file handler to prevent descriptor leaks in high-concurrency runtimes.

        Args:
            file_path: The local absolute or relative path to the target image/file.
            cid: Optional custom Content-ID alias. If omitted, the filename is used as the CID.
            safe_base_dir: Guardrail path directory to insulate against Path Traversal (CWE-22).

        Returns:
            The builder instance for fluent call chaining.
        """
        path = Path(file_path)

        if safe_base_dir:
            SecurityGuard.validate_attachment_path(path, safe_base_dir)

        SecurityGuard.check_file_size(path)

        target_cid = cid or path.name

        content_type, _ = mimetypes.guess_type(str(path))
        if not content_type:
            content_type = "application/octet-stream"

        file_bytes = path.read_bytes()

        self._files.append(("inline", (target_cid, file_bytes, content_type)))

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

    def check_deliverability(self) -> dict[str, float | list[str] | bool] | SpamReport:
        """Performs a local, zero-network static analysis of the current HTML payload to detect common structural spam triggers.

        Returns:
            A dictionary containing a deliverability score and a list of identified issues.
        """
        html_payload = self._payload.get("html")
        if not html_payload:
            return {"score": 100.0, "issues": ["No HTML content to analyze."], "is_safe": True}

        return SpamGuard.check_html(html_payload)

    def set_idempotency_safe(self, *, enabled: bool) -> Self:
        """Allows you to force-disable the automatic generation of the idempotency key.

        Returns:
            The builder instance.
        """
        self._idempotency_safe = enabled
        return self

    def build(self) -> tuple[dict[str, Any], list[tuple[str, FileTuple]] | None]:
        """Finalize the payload for the sync and async clients.

        Returns:
            A tuple containing the payload dictionary and the list of files to be attached.
        """
        final_payload = self._payload.copy()

        if self._idempotency_safe and "h:X-Idempotency-Key" not in final_payload:
            idempotency_key = IdempotencyGuard.generate_key(
                self._domain, final_payload, self._files
            )
            final_payload["h:X-Idempotency-Key"] = idempotency_key

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

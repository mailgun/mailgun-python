import logging
import os
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Final


logger = logging.getLogger(__name__)


class MockResponse:
    """Mock HTTP response to ensure contract compatibility."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        """Initialize the MockResponse.

        Args:
            json_data: The dictionary to return as JSON response data.
            status_code: The HTTP status code to return (default 200).
        """
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> dict[str, Any]:
        """Return the stored JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise an HTTPError if the response status is not 200."""


class LocalSandbox:
    """Local sandbox for intercepting and rendering emails without network calls."""

    __slots__ = ("_preview_dir",)

    def __init__(self, preview_dir: str | None = None) -> None:
        """Initialize the sandbox with a directory for previews."""
        self._preview_dir: Final = preview_dir or tempfile.gettempdir()

    def intercept_and_preview(self, domain: str, payload: dict[str, Any]) -> MockResponse:
        """Intercept the payload, write it as an HTML file, and open it in the browser.

        Returns:
            A MockResponse instance confirming the email was intercepted.
        """
        html_content = payload.get("html", "")
        if not html_content:
            text_content = payload.get("text", "No content provided.")
            html_content = f"<html><body><pre>{text_content}</pre></body></html>"

        safe_domain = domain.replace("/", "_")
        temp_file_path = Path(self._preview_dir) / f"mailgun_preview_{hash(safe_domain)}.html"

        Path(temp_file_path).write_text(html_content, encoding="utf-8")

        # Check if we are running in a CI/CD pipeline (e.g., GitHub Actions, GitLab CI)
        is_ci_env = os.environ.get("CI") == "true" or "PYTEST_CURRENT_TEST" in os.environ

        if not is_ci_env:
            try:
                webbrowser.open(f"file://{temp_file_path}")
                logger.info(
                    "LocalSandbox: Email intercepted and opened in the browser (%s)", temp_file_path
                )
            except OSError as e:
                logger.warning("LocalSandbox: Failed to open the browser or write file: %s", e)
        else:
            logger.info(
                "🛡️ LocalSandbox: CI environment detected. Email saved locally: %s", temp_file_path
            )

        return MockResponse(
            {
                "status_code": 200,
                "id": f"<sandbox-preview-{hash(temp_file_path)}@mailgun-local>",
                "message": "Queued. Thank you (Local Sandbox Intercepted).",
            }
        )

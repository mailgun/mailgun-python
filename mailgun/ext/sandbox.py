import html
import logging
import os
import re
import tempfile
import webbrowser
from typing import Any, Final


logger = logging.getLogger(__name__)

# CWE-79 Defense: Strict Content Security Policy blocking all scripts and plugins
CSP_META: Final = (
    '<meta http-equiv="Content-Security-Policy" '
    "content=\"script-src 'none'; object-src 'none'; base-uri 'none';\">\n"
)


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
        """Raise an HTTPError if the response status is not 2xx.

        Raises:
            ApiError: If the server returns a 4xx or 5xx status code.
        """
        if self.status_code >= 400:  # noqa: PLR2004
            from mailgun.handlers.error_handler import ApiError  # noqa: PLC0415

            msg = f"Mock HTTP Error: {self.status_code} Server Error for url: <sandbox-intercept>"
            raise ApiError(msg)


class LocalSandbox:
    """Local sandbox for intercepting and rendering emails without network calls."""

    __slots__ = ("_open_browser", "_preview_dir")

    def __init__(self, preview_dir: str | None = None, *, open_browser: bool = False) -> None:
        """Initialize the sandbox.

        Args:
            preview_dir: Custom directory to save the HTML files.
            open_browser: Whether to attempt opening the default system web browser.
        """
        self._preview_dir: Final = preview_dir or tempfile.gettempdir()

        # Guardrail against Fuzzer/Test suite browser-tab explosions
        env_disable = os.environ.get("MAILGUN_DISABLE_BROWSER", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self._open_browser: Final = open_browser and not env_disable

    def intercept_and_preview(self, payload: dict[str, Any]) -> MockResponse:
        """Intercept the payload, write it as an HTML file, and open it in the browser.

        Returns:
            A MockResponse instance confirming the email was intercepted.
        """
        html_content = payload.get("html", "")

        if not html_content:
            text_content = payload.get("text") or "No content provided."
            safe_text = html.escape(str(text_content))
            html_content = (
                f"<!DOCTYPE html>\n<html>\n<head>\n{CSP_META}</head>\n"
                f"<body>\n<pre>{safe_text}</pre>\n</body>\n</html>"
            )
        # Inject CSP into existing HTML content to prevent malicious script execution (CWE-79)
        elif re.search(r"<head[^>]*>", html_content, re.IGNORECASE):
            html_content = re.sub(
                r"(<head[^>]*>)",
                rf"\1\n{CSP_META}",
                html_content,
                count=1,
                flags=re.IGNORECASE,
            )
        elif re.search(r"<html[^>]*>", html_content, re.IGNORECASE):
            html_content = re.sub(
                r"(<html[^>]*>)",
                rf"\1\n<head>\n{CSP_META}</head>\n",
                html_content,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            # Wrap raw HTML snippets safely
            html_content = (
                f"<!DOCTYPE html>\n<html>\n<head>\n{CSP_META}</head>\n"
                f"<body>\n{html_content}\n</body>\n</html>"
            )

        fd, temp_file_path = tempfile.mkstemp(
            prefix="mailgun_preview_", suffix=".html", dir=self._preview_dir
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Check if we are running in a CI/CD pipeline (e.g., GitHub Actions, GitLab CI)
        is_ci_env = os.environ.get("CI") == "true" or "PYTEST_CURRENT_TEST" in os.environ

        if self._open_browser and not is_ci_env:
            try:
                webbrowser.open(f"file://{temp_file_path}")
                logger.info(
                    "LocalSandbox: Email intercepted and opened in the browser (%s)", temp_file_path
                )
            except OSError as e:
                logger.warning("LocalSandbox: Failed to open the browser or write file: %s", e)
        else:
            logger.info(
                "LocalSandbox: Browser preview disabled or CI detected. Email saved locally: %s",
                temp_file_path,
            )

        return MockResponse(
            {
                "status_code": 200,
                "id": f"<sandbox-preview-{hash(temp_file_path)}@mailgun-local>",
                "message": "Queued. Thank you (Local Sandbox Intercepted).",
            }
        )

from __future__ import annotations

import logging
import os
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Final


logger = logging.getLogger(__name__)

CSP_META: Final = (
    '<meta http-equiv="Content-Security-Policy" '
    "content=\"script-src 'none'; object-src 'none'; base-uri 'none';\">\\n"
)


class MockResponse:
    """Mock HTTP response to ensure contract compatibility."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        """Initialize MockResponse.

        Args:
            json_data: The JSON response dictionary.
            status_code: The HTTP status code.
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

            msg = f"Mock HTTP Error: {self.status_code}"
            raise ApiError(msg)


class SandboxEndpoint:
    """Mock endpoint helper for LocalSandbox."""

    def __init__(self, sandbox: LocalSandbox, endpoint_name: str) -> None:
        """Initialize SandboxEndpoint.

        Args:
            sandbox: The LocalSandbox instance.
            endpoint_name: The name of the endpoint.
        """
        self.sandbox = sandbox
        self.endpoint_name = endpoint_name

    def create(self, *_args: Any, **_kwargs: Any) -> MockResponse:
        """Mock create request.

        Args:
            *_args: Variable positional arguments.
            **_kwargs: Variable keyword arguments.

        Returns:
            A MockResponse instance.
        """
        if self.sandbox.preview_dir:
            self.sandbox.preview_dir.mkdir(parents=True, exist_ok=True)
            preview_file = self.sandbox.preview_dir / f"{self.endpoint_name}_create.json"
            preview_file.write_text('{"message": "sandbox preview generated"}')
        return MockResponse({"message": "success", "endpoint": self.endpoint_name}, status_code=200)

    @staticmethod
    def get(*_args: Any, **_kwargs: Any) -> MockResponse:
        """Mock get request.

        Args:
            *_args: Variable positional arguments.
            **_kwargs: Variable keyword arguments.

        Returns:
            A MockResponse instance.
        """
        return MockResponse({"items": []}, status_code=200)

    @staticmethod
    def update(*_args: Any, **_kwargs: Any) -> MockResponse:
        """Mock update request.

        Args:
            *_args: Variable positional arguments.
            **_kwargs: Variable keyword arguments.

        Returns:
            A MockResponse instance.
        """
        return MockResponse({"message": "updated"}, status_code=200)

    @staticmethod
    def delete(*_args: Any, **_kwargs: Any) -> MockResponse:
        """Mock delete request.

        Args:
            *_args: Variable positional arguments.
            **_kwargs: Variable keyword arguments.

        Returns:
            A MockResponse instance.
        """
        return MockResponse({"message": "deleted"}, status_code=200)


class LocalSandbox:
    """Local sandbox for intercepting and rendering emails without network calls."""

    def __init__(
        self, preview_dir: Path | str | None = None, *, open_browser: bool = False
    ) -> None:
        """Initialize LocalSandbox.

        Args:
            preview_dir: Directory to save preview files.
            open_browser: Whether to open the browser automatically.
        """
        self.preview_dir = Path(preview_dir) if preview_dir else Path(tempfile.gettempdir())
        self._open_browser = open_browser

    def __getattr__(self, name: str) -> Any:
        """Resolve endpoint attributes dynamically.

        Args:
            name: Attribute name.

        Returns:
            A SandboxEndpoint instance.

        Raises:
            AttributeError: If the attribute name represents a dunder/magic method.
        """
        if name.startswith("__") and name.endswith("__"):
            msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
            raise AttributeError(msg)
        return SandboxEndpoint(self, name)

    def intercept_and_preview(self, payload: dict[str, Any]) -> MockResponse:
        """Intercept the payload, write it as an HTML file, and open it in the browser.

        Args:
            payload: Email payload dictionary.

        Returns:
            A MockResponse instance confirming interception.
        """
        html_content = payload.get("html") or payload.get("text") or "Sandbox Preview"
        if "<html>" not in html_content.lower():
            html_content = (
                f"<!DOCTYPE html>\n<html>\n<head>\n{CSP_META}</head>\n"
                f"<body>\n<pre>{html_content}</pre>\n</body>\n</html>"
            )
        else:
            html_content = (
                f"<!DOCTYPE html>\n<html>\n<head>\n{CSP_META}</head>\n"
                f"<body>\n{html_content}\n</body>\n</html>"
            )

        fd, temp_file_path = tempfile.mkstemp(
            prefix="mailgun_preview_", suffix=".html", dir=self.preview_dir
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_content)

        is_ci_env = os.environ.get("CI") == "true" or "PYTEST_CURRENT_TEST" in os.environ
        if self._open_browser and not is_ci_env:
            try:
                webbrowser.open(f"file://{temp_file_path}")
            except OSError as e:
                logger.warning("LocalSandbox: Failed to open browser: %s", e)

        return MockResponse(
            {"id": "<sandbox-preview>", "message": "Queued. Thank you."}, status_code=200
        )

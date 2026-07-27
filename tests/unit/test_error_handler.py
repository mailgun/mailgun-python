"""Unit tests for custom API exception classes in error_handler.py."""


from mailgun.handlers.error_handler import (
    ApiError,
    DeliverabilityError,
    MailgunTimeoutError,
    RouteNotFoundError,
    UploadError,
)


class TestErrorHandlerExceptions:
    """Verifies instantiation, inheritance hierarchy, and string formatting."""

    def test_api_error_base(self) -> None:
        err = ApiError("Base API failure")
        assert str(err) == "Base API failure"
        assert isinstance(err, Exception)

    def test_mailgun_timeout_error(self) -> None:
        err = MailgunTimeoutError("Request timed out after 60s")
        assert str(err) == "Request timed out after 60s"
        assert isinstance(err, ApiError)
        assert isinstance(err, TimeoutError)

    def test_route_not_found_error(self) -> None:
        err = RouteNotFoundError("Route /v9/invalid not found")
        assert str(err) == "Route /v9/invalid not found"
        assert isinstance(err, ApiError)

    def test_upload_error(self) -> None:
        err = UploadError("Attachment exceeds 25MB threshold")
        assert str(err) == "Attachment exceeds 25MB threshold"
        assert isinstance(err, ApiError)

    def test_deliverability_error_formatting(self) -> None:
        issues = ["Missing alt tag on image", "<script> tag detected"]
        err = DeliverabilityError(score=35.0, issues=issues)

        assert err.score == 35.0
        assert err.issues == issues
        assert isinstance(err, ApiError)

        formatted_str = str(err)
        assert "HTML Deliverability Check Failed (Score: 35.0/100)." in formatted_str
        assert "The payload was blocked to protect your domain reputation." in formatted_str
        assert "Please fix the following issues:" in formatted_str
        assert "  - Missing alt tag on image" in formatted_str
        assert "  - <script> tag detected" in formatted_str

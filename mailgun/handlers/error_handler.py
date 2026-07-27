"""Provide custom exceptions for API error handling.

Exceptions:
    - ApiError: Base exception for API errors.
    - MailgunTimeoutError: Raised when a request to the Mailgun API times out.
    - RouteNotFoundError: Raised when the requested endpoint cannot be resolved.
    - UploadError: Raised when the maximum message size is greater than 25 MB.
"""

from __future__ import annotations


__all__ = [
    "ApiError",
    "MailgunTimeoutError",
    "RouteNotFoundError",
    "UploadError",
]


class ApiError(Exception):
    """Base class for all API-related errors.

    This exception serves as the root for all custom API error types,
    allowing for more specific error handling based on the type of API
    failure encountered.
    """


class MailgunTimeoutError(ApiError, TimeoutError):
    """Raised when a request to the Mailgun API times out."""


class RouteNotFoundError(ApiError):
    """Raised when the requested Mailgun endpoint cannot be resolved."""


class UploadError(ApiError):
    """Raised when the maximum message size is greater than 25 MB."""


class DeliverabilityError(ApiError):
    """Raised when SpamGuard detects critical structural flaws in the HTML payload that would severely penalize domain reputation or trigger spam filters."""

    def __init__(self, score: float, issues: list[str]) -> None:
        self.score = score
        self.issues = issues

        # Format a highly readable, bulleted message for the console
        formatted_issues = "\n  - ".join(issues)
        message = (
            f"HTML Deliverability Check Failed (Score: {score}/100).\n"
            f"The payload was blocked to protect your domain reputation. "
            f"Please fix the following issues:\n  - {formatted_issues}"
        )
        super().__init__(message)

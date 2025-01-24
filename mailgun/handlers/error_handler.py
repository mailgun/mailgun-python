"""ERROR HANDLER.

Exceptions:
    - ApiError: Base exception for API errors.
"""


class ApiError(Exception):
    """Base class for all API-related errors.

    This exception serves as the root for all custom API error types,
    allowing for more specific error handling based on the type of API
    failure encountered.
    """

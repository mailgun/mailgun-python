"""Unit tests for mailgun.handlers.error_handler."""

import pytest

from mailgun.handlers.error_handler import ApiError


class TestApiError:
    """Tests for ApiError exception."""

    def test_api_error_is_exception(self) -> None:
        assert issubclass(ApiError, Exception)

    def test_api_error_message(self) -> None:
        err = ApiError("Domain is missing!")
        assert str(err) == "Domain is missing!"

    def test_api_error_can_be_raised(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            raise ApiError("Storage url is required")
        assert exc_info.value.args[0] == "Storage url is required"

    def test_api_error_with_cause(self) -> None:
        try:
            raise ValueError("inner")
        except ValueError as e:
            try:
                raise ApiError("wrapped") from e
            except ApiError as err:
                assert str(err) == "wrapped"
                assert err.__cause__ is not None

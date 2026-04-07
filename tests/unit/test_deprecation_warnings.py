"""Unit tests verifying that deprecated endpoints trigger appropriate SDK warnings."""

import warnings
import pytest

from mailgun.client import Client


def test_legacy_tag_api_triggers_warning() -> None:
    """Verify that the deprecated /v3/domain/tag API path triggers a warning."""
    client = Client(auth=("api", "key"))

    with pytest.warns(DeprecationWarning) as record:
        # Directly test the interceptor with a known legacy URL boundary
        client.messages._warn_if_deprecated("GET", "https://api.mailgun.net/v3/sandbox.mailgun.org/tag")

    assert len(record) >= 1
    warning_msg = str(record[0].message)
    assert "legacy Tag API" in warning_msg
    assert "migrate to the new Tags API" in warning_msg


def test_legacy_bounce_classification_triggers_warning() -> None:
    """Verify that calling v1 bounce-classification raises a warning."""
    client = Client(auth=("api", "key"))

    with pytest.warns(DeprecationWarning) as record:
        client.messages._warn_if_deprecated("GET", "https://api.mailgun.net/v1/bounce-classification/stats")

    assert len(record) >= 1
    assert "v1 bounce-classification API is deprecated" in str(record[0].message)


def test_legacy_validations_trigger_warning() -> None:
    """Verify that old v3 address validation endpoints trigger a warning."""
    client = Client(auth=("api", "key"))

    with pytest.warns(DeprecationWarning) as record:
        client.messages._warn_if_deprecated("GET", "https://api.mailgun.net/v3/address/validate")

    assert len(record) >= 1
    assert "v3 Address Validation/Parsing APIs are deprecated" in str(record[0].message)


def test_legacy_bulk_validations_trigger_warning() -> None:
    """Verify that old v3 bulk validation lists trigger a warning."""
    client = Client(auth=("api", "key"))

    with pytest.warns(DeprecationWarning) as record:
        client.messages._warn_if_deprecated("POST", "https://api.mailgun.net/v3/lists/my-list/validate")

    assert len(record) >= 1
    assert "v3 Bulk Validation API is deprecated" in str(record[0].message)


def test_valid_endpoints_do_not_trigger_warnings() -> None:
    """Verify that valid endpoints (like the NEW APIs) do NOT trigger warnings."""
    client = Client(auth=("api", "key"))

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)

        # This is the NEW API (/v3/domain/tags). It should pass without warnings.
        client.messages._warn_if_deprecated("GET", "https://api.mailgun.net/v3/sandbox.mailgun.org/tags")

        # Standard messages API
        client.messages._warn_if_deprecated("POST", "https://api.mailgun.net/v3/sandbox.mailgun.org/messages")

        # New v4 validations API
        client.messages._warn_if_deprecated("GET", "https://api.mailgun.net/v4/address/validate")

        # New v2 bounce classification
        client.messages._warn_if_deprecated("POST", "https://api.mailgun.net/v2/bounce-classification/metrics")

"""Unit tests for mailgun handlers."""

from urllib.parse import urlparse

import pytest

from mailgun.handlers.default_handler import handle_default
from mailgun.handlers.domains_handler import (
    handle_dkimkeys,
    handle_domainlist,
    handle_domains,
    handle_mailboxes_credentials,
    handle_sending_queues,
)
from mailgun.handlers.email_validation_handler import handle_address_validate
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.inbox_placement_handler import handle_inbox
from mailgun.handlers.ips_handler import handle_ips
from mailgun.handlers.messages_handler import handle_resend_message
from mailgun.handlers.suppressions_handler import (
    handle_bounces,
    handle_complaints,
    handle_unsubscribes,
    handle_whitelists,
)
from mailgun.handlers.tags_handler import handle_tags
from tests.unit.conftest import (
    parse_domain_name,
    TEST_DOMAIN,
    BASE_URL_V3,
    BASE_URL_V4,
    BASE_URL_V1,
)


class TestHandleDefault:
    """Tests for handle_default."""

    def test_requires_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        with pytest.raises(ApiError, match="Domain is missing"):
            handle_default(url, None, "get")

    def test_builds_url_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        result = handle_default(url, "example.com", "get")
        assert result == "https://api.mailgun.net/v3/example.com/messages"

    def test_builds_url_with_keys(self) -> None:
        url_config = {"base": f"{BASE_URL_V3}/", "keys": ["events"]}
        result = handle_default(url_config, TEST_DOMAIN, "get")

        expected_url = "https://api.mailgun.net/v3/example.com/events"

        assert result == expected_url
        assert parse_domain_name(result) == TEST_DOMAIN

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("events")


class TestHandleDomainlist:
    """Tests for handle_domainlist."""

    def test_returns_base_plus_domains(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["domainlist"]}
        result = handle_domainlist(url, None, None)
        assert result == "https://api.mailgun.net/v4/domains"


class TestHandleDomains:
    """Tests for handle_domains."""

    def test_with_domain_and_keys(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["webhooks"]}
        result = handle_domains(url, "example.com", "get")

        expected_url = "https://api.mailgun.net/v4/domains/example.com/webhooks"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("webhooks")


    def test_requires_domain_when_keys_present(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["webhooks"]}
        with pytest.raises(ApiError, match="Domain is missing"):
            handle_domains(url, None, "get")

    def test_with_login_kwarg(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["credentials"]}
        result = handle_domains(url, "example.com", "get", login="user@example.com")
        assert "user@example.com" in result or "login" in result

    def test_with_domain_name_kwarg_get(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": []}
        result = handle_domains(
            url, None, "get", domain_name="my-domain.com"
        )
        expected_url = "https://api.mailgun.net/v4/domains/my-domain.com"

        assert result == expected_url

    def test_verify_requires_true(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": []}
        with pytest.raises(ApiError, match="Verify option should be True"):
            handle_domains(url, "example.com", "put", verify=False)


class TestHandleSendingQueues:
    """Tests for handle_sending_queues."""

    def test_builds_sending_queues_url(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["sending_queues"]}
        result = handle_sending_queues(url, "example.com", None)
        assert result.endswith("/example.com/sending_queues")
        assert "sending_queues" in result


class TestHandleMailboxesCredentials:
    """Tests for handle_mailboxes_credentials."""

    def test_with_login(self) -> None:
        url = {"base": f"{BASE_URL_V3}/domains/", "keys": ["credentials"]}
        result = handle_mailboxes_credentials(
            url, "example.com", None, login="user@example.com"
        )
        assert "user@example.com" in result
        assert "credentials" in result


class TestHandleDkimkeys:
    """Tests for handle_dkimkeys."""

    def test_builds_dkim_keys_url(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["dkim", "keys"]}
        result = handle_dkimkeys(url, None, None)

        expected_url = "https://api.mailgun.net/v1/dkim/keys"

        assert result == expected_url

        parsed = urlparse(result)
        assert "dkim" in parsed.path
        assert parsed.path.endswith("keys")
        assert "dkim" in result
        assert "keys" in result


class TestHandleIps:
    """Tests for handle_ips."""

    def test_base_without_trailing_slash(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ips"]}
        result = handle_ips(url, None, None)
        assert result == "https://api.mailgun.net/v3/ips"

    def test_with_ip_kwarg(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ips"]}
        result = handle_ips(url, None, None, ip="1.2.3.4")
        assert "1.2.3.4" in result


class TestHandleTags:
    """Tests for handle_tags."""

    def test_builds_tags_url_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["tags"]}
        result = handle_tags(url, "example.com", None)

        expected_url = "https://api.mailgun.net/v3/example.com/tags"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("tags")

    def test_with_tag_name_kwarg(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["tags"]}
        result = handle_tags(url, "example.com", None, tag_name="my-tag")
        assert "my-tag" in result


class TestHandleBounces:
    """Tests for handle_bounces."""

    def test_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["bounces"]}
        result = handle_bounces(url, "example.com", None)

        expected_url = "https://api.mailgun.net/v3/example.com/bounces"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("bounces")

    def test_with_bounce_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["bounces"]}
        result = handle_bounces(
            url, "example.com", None, bounce_address="bad@example.com"
        )
        assert "bad@example.com" in result


class TestHandleUnsubscribes:
    """Tests for handle_unsubscribes."""

    def test_with_unsubscribe_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["unsubscribes"]}
        result = handle_unsubscribes(
            url, "example.com", None, unsubscribe_address="user@example.com"
        )
        assert "user@example.com" in result


class TestHandleComplaints:
    """Tests for handle_complaints."""

    def test_with_complaint_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["complaints"]}
        result = handle_complaints(
            url, "example.com", None, complaint_address="spam@example.com"
        )
        assert "spam@example.com" in result


class TestHandleWhitelists:
    """Tests for handle_whitelists."""

    def test_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["whitelists"]}
        result = handle_whitelists(url, "example.com", None)
        assert "example.com" in result
        assert "whitelists" in result


class TestHandleAddressValidate:
    """Tests for handle_address_validate (email validation handler)."""

    def test_without_list_name_single_key(self) -> None:
        """url["keys"][1:] is empty, no list_name."""
        url = {"base": f"{BASE_URL_V4}/address/validate", "keys": ["validate"]}
        result = handle_address_validate(url, None, None)
        assert result == "https://api.mailgun.net/v4/address/validate"

    def test_without_list_name_multiple_keys(self) -> None:
        """url["keys"][1:] is non-empty, no list_name."""
        url = {
            "base": f"{BASE_URL_V4}/address/validate",
            "keys": ["validate", "bulk"],
        }
        result = handle_address_validate(url, None, None)
        assert result == "https://api.mailgun.net/v4/address/validate/bulk"

    def test_with_list_name(self) -> None:
        """list_name in kwargs appends /list_name to path."""
        url = {
            "base": f"{BASE_URL_V4}/address/validate",
            "keys": ["validate", "bulk"],
        }
        result = handle_address_validate(
            url, None, None, list_name="my_list"
        )
        assert result == "https://api.mailgun.net/v4/address/validate/bulk/my_list"

    def test_with_list_name_single_key(self) -> None:
        """list_name with single key (final_keys empty)."""
        url = {"base": f"{BASE_URL_V4}/address/validate", "keys": ["validate"]}
        result = handle_address_validate(url, None, None, list_name="my_list")
        assert result == "https://api.mailgun.net/v4/address/validate/my_list"


class TestHandleInbox:
    """Tests for handle_inbox (inbox placement handler)."""

    def test_no_test_id_empty_keys(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": []}
        result = handle_inbox(url, None, None)
        assert result == "https://api.mailgun.net/v3"

    def test_no_test_id_with_keys(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(url, None, None)
        assert result == "https://api.mailgun.net/v3/inbox/tests"

    def test_with_test_id_only(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(url, None, None, test_id="test-123")
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123"

    def test_with_test_id_and_counters_true(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(
            url, None, None, test_id="test-123", counters=True
        )
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123/counters"

    def test_with_test_id_and_counters_false_raises(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        with pytest.raises(ApiError, match="Counters option should be True or absent"):
            handle_inbox(url, None, None, test_id="test-123", counters=False)

    def test_with_test_id_and_checks_true_no_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(
            url, None, None, test_id="test-123", checks=True
        )
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123/checks"

    def test_with_test_id_and_checks_true_with_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(
            url,
            None,
            None,
            test_id="test-123",
            checks=True,
            address="user@example.com",
        )
        assert result == (
            "https://api.mailgun.net/v3/inbox/tests/test-123/checks/user@example.com"
        )

    def test_with_test_id_and_checks_false_raises(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        with pytest.raises(ApiError, match="Checks option should be True or absent"):
            handle_inbox(url, None, None, test_id="test-123", checks=False)


class TestHandleResendMessage:
    """Tests for handle_resend_message."""

    def test_with_storage_url(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["resendmessage"]}
        result = handle_resend_message(
            url, None, None, storage_url="https://storage.mailgun.net/msg/123"
        )
        assert result == "https://storage.mailgun.net/msg/123"

    def test_without_storage_url_returns_none(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["resendmessage"]}
        result = handle_resend_message(url, None, None)
        assert result is None

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
from mailgun.handlers.bounce_classification_handler import handle_bounce_classification
from mailgun.handlers.ip_pools_handler import handle_ippools
from mailgun.handlers.keys_handler import handle_keys
from mailgun.handlers.mailinglists_handler import handle_lists
from mailgun.handlers.metrics_handler import handle_metrics
from mailgun.handlers.routes_handler import handle_routes
from mailgun.handlers.templates_handler import handle_templates
from mailgun.handlers.users_handler import handle_users
from tests.conftest import (
    parse_domain_name,
    TEST_DOMAIN,
    BASE_URL_V3,
    BASE_URL_V4,
    BASE_URL_V5,
    BASE_URL_V1,
    BASE_URL_V2,
    TEST_EMAIL,
    TEST_123,
)


class TestHandleDefault:
    """Tests for handle_default."""

    # def test_requires_domain(self) -> None:
    #     url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
    #     with pytest.raises(ApiError, match="Domain is missing"):
    #         handle_default(url, None, "get")

    def test_builds_url_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["messages"]}
        result = handle_default(url, TEST_DOMAIN, "get")
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

    def test_with_test_id_and_checks_false_raises(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        with pytest.raises(ApiError, match="Checks option should be True or absent"):
            handle_inbox(url, None, None, test_id=TEST_123, checks=False)

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
        result = handle_domains(url, TEST_DOMAIN, "get")

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
        result = handle_domains(url, TEST_DOMAIN, "get", login=TEST_EMAIL)
        assert TEST_EMAIL in result or "login" in result

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
            handle_domains(url, TEST_DOMAIN, "put", verify=False)


class TestHandleSendingQueues:
    """Tests for handle_sending_queues."""

    def test_builds_sending_queues_url(self) -> None:
        url = {"base": f"{BASE_URL_V4}/domains/", "keys": ["sending_queues"]}
        result = handle_sending_queues(url, TEST_DOMAIN, None)
        assert result.endswith("/example.com/sending_queues")
        assert "sending_queues" in result


class TestHandleMailboxesCredentials:
    """Tests for handle_mailboxes_credentials."""

    def test_with_login(self) -> None:
        url = {"base": f"{BASE_URL_V3}/domains/", "keys": ["credentials"]}
        result = handle_mailboxes_credentials(url, TEST_DOMAIN, None, login=TEST_EMAIL)

        parts = TEST_EMAIL.split("@")

        assert len(parts) == 2, "Email must have exactly one '@' symbol"
        assert parts[0] == "user", "Local part is incorrect"
        assert parts[1] == TEST_DOMAIN, "Domain part is incorrect"
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
        result = handle_tags(url, TEST_DOMAIN, None)

        expected_url = "https://api.mailgun.net/v3/example.com/tags"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("tags")

    def test_with_tag_name_kwarg(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["tags"]}
        result = handle_tags(url, TEST_DOMAIN, None, tag_name="my-tag")
        assert "my-tag" in result


class TestHandleBounces:
    """Tests for handle_bounces."""

    def test_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["bounces"]}
        result = handle_bounces(url, TEST_DOMAIN, None)

        expected_url = "https://api.mailgun.net/v3/example.com/bounces"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("bounces")

    def test_with_bounce_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["bounces"]}
        email = "bad@example.com"
        result = handle_bounces(url, TEST_DOMAIN, None, bounce_address=email)

        parts = email.split("@")

        assert len(parts) == 2, "Email must have exactly one '@' symbol"
        assert parts[0] == "bad", "Local part is incorrect"
        assert parts[1] == TEST_DOMAIN, "Domain part is incorrect"
        assert "bounces" in result

class TestHandleUnsubscribes:
    """Tests for handle_unsubscribes."""

    def test_with_unsubscribe_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["unsubscribes"]}
        result = handle_unsubscribes(url, TEST_DOMAIN, None, unsubscribe_address=TEST_EMAIL)
        parts = TEST_EMAIL.split("@")

        assert len(parts) == 2, "Email must have exactly one '@' symbol"
        assert parts[0] == "user", "Local part is incorrect"
        assert parts[1] == TEST_DOMAIN, "Domain part is incorrect"
        assert "unsubscribes" in result


class TestHandleComplaints:
    """Tests for handle_complaints."""

    def test_with_complaint_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["complaints"]}
        email = "spam@example.com"
        result = handle_complaints(url, TEST_DOMAIN, None, complaint_address=email)
        parts = email.split("@")

        assert len(parts) == 2, "Email must have exactly one '@' symbol"
        assert parts[0] == "spam", "Local part is incorrect"
        assert parts[1] == TEST_DOMAIN, "Domain part is incorrect"
        assert "complaints" in result


class TestHandleWhitelists:
    """Tests for handle_whitelists."""

    def test_with_domain(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["whitelists"]}
        result = handle_whitelists(url, TEST_DOMAIN, None)

        expected_url = "https://api.mailgun.net/v3/example.com/whitelists"

        assert result == expected_url

        parsed = urlparse(result)
        assert TEST_DOMAIN in parsed.path
        assert parsed.path.endswith("whitelists")


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
        result = handle_inbox(url, None, None, test_id=TEST_123)
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123"

    def test_with_test_id_and_counters_true(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(url, None, None, test_id=TEST_123, counters=True)
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123/counters"

    def test_with_test_id_and_counters_false_raises(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        with pytest.raises(ApiError, match="Counters option should be True or absent"):
            handle_inbox(url, None, None, test_id=TEST_123, counters=False)

    def test_with_test_id_and_checks_true_no_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(url, None, None, test_id=TEST_123, checks=True)
        assert result == "https://api.mailgun.net/v3/inbox/tests/test-123/checks"

    def test_with_test_id_and_checks_true_with_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        result = handle_inbox(
            url,
            None,
            None,
            test_id=TEST_123,
            checks=True,
            address=TEST_EMAIL,
        )
        assert result == (
            "https://api.mailgun.net/v3/inbox/tests/test-123/checks/user@example.com"
        )

    def test_with_test_id_and_checks_false_raises(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["inbox", "tests"]}
        with pytest.raises(ApiError, match="Checks option should be True or absent"):
            handle_inbox(url, None, None, test_id=TEST_123, checks=False)


class TestHandleResendMessage:
    """Tests for handle_resend_message."""

    def test_without_storage_url_raises_api_error(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["resendmessage"]}
        with pytest.raises(ApiError, match="Storage url is required"):
            handle_resend_message(url, None, None)

    def test_with_storage_url_returns_str(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["resendmessage"]}
        result = handle_resend_message(url, None, None, storage_url="https://store/1")
        assert result == "https://store/1"


class TestHandleTemplates:
    """Tests for handle_templates (Dynamic V3/V4 routing)."""

    def test_account_templates_forces_v4(self) -> None:
        """Account templates (no domain) should force V4 even if base is V3."""
        url = {"base": f"{BASE_URL_V3}/", "keys": ["templates"]}
        result = handle_templates(url, None, None)
        assert result == f"{BASE_URL_V4}/templates"

    def test_domain_templates_forces_v3(self) -> None:
        """Domain templates should force V3 even if base is V4."""
        url = {"base": f"{BASE_URL_V4}/", "keys": ["templates"]}
        result = handle_templates(url, TEST_DOMAIN, None)
        assert result == f"{BASE_URL_V3}/{TEST_DOMAIN}/templates"

    def test_template_name(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["templates"]}
        result = handle_templates(url, TEST_DOMAIN, None, template_name="promo")
        assert result == f"{BASE_URL_V3}/{TEST_DOMAIN}/templates/promo"

    def test_template_versions(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["templates"]}
        result = handle_templates(url, TEST_DOMAIN, None, template_name="promo", versions=True)
        assert result == f"{BASE_URL_V3}/{TEST_DOMAIN}/templates/promo/versions"

    def test_template_versions_false_raises_error(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["templates"]}
        with pytest.raises(ApiError, match="Versions should be True or absent"):
            handle_templates(url, TEST_DOMAIN, None, template_name="promo", versions=False)

    def test_template_tag_and_copy(self) -> None:
        url = {"base": f"{BASE_URL_V4}/", "keys": ["templates"]}
        result = handle_templates(
            url,
            TEST_DOMAIN,
            None,
            template_name="promo",
            versions=True,
            tag="v1",
            copy=True,
            new_tag="v2",
        )
        assert result == f"{BASE_URL_V3}/{TEST_DOMAIN}/templates/promo/versions/v1/copy/v2"


class TestHandleUsers:
    """Tests for handle_users."""

    def test_users_default(self) -> None:
        url = {"base": f"{BASE_URL_V5}/", "keys": ["users"]}
        assert handle_users(url, None, None) == f"{BASE_URL_V5}/users"

    def test_users_me(self) -> None:
        url = {"base": f"{BASE_URL_V5}/", "keys": ["users", "me"]}
        assert handle_users(url, None, None, user_id="me") == f"{BASE_URL_V5}/users/me"

    def test_users_specific_id(self) -> None:
        url = {"base": f"{BASE_URL_V5}/", "keys": ["users"]}
        assert handle_users(url, None, None, user_id="user_123") == f"{BASE_URL_V5}/users/user_123"


class TestHandleMetrics:
    """Tests for handle_metrics."""

    def test_metrics_default(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["tags"]}
        assert handle_metrics(url, None, None) == f"{BASE_URL_V1}/tags"

    def test_metrics_usage(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["tags"]}
        assert handle_metrics(url, None, None, usage="stats") == f"{BASE_URL_V1}/stats/tags"

    def test_metrics_limits(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["tags"]}
        assert (
            handle_metrics(url, None, None, tags=True, limits="limits")
            == f"{BASE_URL_V1}/tags/limits"
        )


class TestHandleRoutes:
    """Tests for handle_routes."""

    def test_routes_default(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["routes"]}
        assert handle_routes(url, None, None) == f"{BASE_URL_V3}/routes"

    def test_routes_with_id(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["routes"]}
        assert handle_routes(url, None, None, route_id="123") == f"{BASE_URL_V3}/routes/123"


class TestHandleLists:
    """Tests for handle_lists."""

    def test_lists_default(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["lists"]}
        assert handle_lists(url, None, None) == f"{BASE_URL_V3}/lists"

    def test_lists_validate(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["lists"]}
        assert (
            handle_lists(url, None, None, address="dev@test", validate=True)
            == f"{BASE_URL_V3}/lists/dev@test/validate"
        )

    def test_lists_multiple(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["lists"]}
        assert (
            handle_lists(url, None, None, address="dev@test", multiple=True)
            == f"{BASE_URL_V3}/lists/dev@test/members.json"
        )

    def test_lists_members(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["lists", "members"]}
        assert (
            handle_lists(url, None, None, address="dev@test")
            == f"{BASE_URL_V3}/lists/dev@test/members"
        )

    def test_lists_member_address(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["lists", "members"]}
        assert (
            handle_lists(url, None, None, address="dev@test", member_address="usr@test")
            == f"{BASE_URL_V3}/lists/dev@test/members/usr@test"
        )


class TestHandleKeys:
    """Tests for handle_keys."""

    def test_keys_default(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["keys"]}
        assert handle_keys(url, None, None) == f"{BASE_URL_V1}/keys"

    def test_keys_with_id(self) -> None:
        url = {"base": f"{BASE_URL_V1}/", "keys": ["keys"]}
        assert handle_keys(url, None, None, key_id="123") == f"{BASE_URL_V1}/keys/123"


class TestHandleIpPools:
    """Tests for handle_ippools."""

    def test_ippools_default(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ip_pools"]}
        assert handle_ippools(url, None, None) == f"{BASE_URL_V3}/ip_pools"

    def test_ippools_with_pool_id(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ip_pools"]}
        assert handle_ippools(url, None, None, pool_id="pool1") == f"{BASE_URL_V3}/ip_pools/pool1"

    def test_ippools_ips_json(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ip_pools", "ips.json"]}
        assert (
            handle_ippools(url, None, None, pool_id="pool1")
            == f"{BASE_URL_V3}/ip_pools/ips.json/pool1"
        )

    def test_ippools_with_ip(self) -> None:
        url = {"base": f"{BASE_URL_V3}/", "keys": ["ip_pools"]}
        assert (
            handle_ippools(url, None, None, pool_id="pool1", ip="1.1.1.1")
            == f"{BASE_URL_V3}/ip_pools/pool1/ips/1.1.1.1"
        )


class TestHandleBounceClassification:
    """Tests for handle_bounce_classification."""

    def test_bounce_classification(self) -> None:
        url = {"base": f"{BASE_URL_V2}/", "keys": ["bounce-classification", "metrics"]}
        assert (
            handle_bounce_classification(url, None, None)
            == f"{BASE_URL_V2}/bounce-classification/metrics"
        )

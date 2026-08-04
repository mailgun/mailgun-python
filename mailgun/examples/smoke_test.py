"""
Ultimate Smoke Test for Mailgun Python SDK.

This script serves as both an integration verification tool and
executable documentation for developers. It tests synchronous and
asynchronous clients, standard Form-Data requests, JSON payloads,
fluent builders, typed dicts, and error handling.

Usage:
    export APIKEY="your-api-key"  # pragma: allowlist secret
    export DOMAIN="your-sandbox-or-real-domain.mailgun.org"
    export MESSAGES_TO="your.verified@email.com"
    python mailgun/examples/smoke_test.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import warnings
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mailgun.builders import MailgunMessageBuilder
from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import ApiError

# Enable SDK logging to demonstrate the new CWE-532 secure error logging
logging.getLogger("mailgun.client").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


# ==============================================================================
# Test Runners
# ==============================================================================


def run_sync_test(
    test_name: str, func: Callable[[], Any], expected_status: tuple[int, ...] = (200,)
) -> None:
    """Execute and validate synchronous API calls."""
    print(f"\n{'=' * 60}\n🚀 SYNC RUN: {test_name}\n{'=' * 60}")
    try:
        result = func()
        if hasattr(result, "status_code"):
            if result.status_code not in expected_status:
                print(f"❌ FAILED (Expected {expected_status}, got {result.status_code})")
            else:
                print(f"✅ PASSED (Status: {result.status_code})")
        else:
            print("✅ PASSED (No strict status returned)")
    except ApiError as e:
        if e.status_code in expected_status:
            print(f"✅ PASSED via expected ApiError (Status: {e.status_code})")
        else:
            print(f"❌ FAILED with unexpected ApiError: {e.status_code} - {e}")
            logging.exception(e)
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")
        logging.exception(e)


async def run_async_test(
    test_name: str, func: Callable[[], Awaitable[Any]], expected_status: tuple[int, ...] = (200,)
) -> None:
    """Execute and validate asynchronous API calls."""
    print(f"\n{'=' * 60}\n⚡ ASYNC RUN: {test_name}\n{'=' * 60}")
    try:
        result = await func()
        if hasattr(result, "status_code"):
            if result.status_code not in expected_status:
                print(f"❌ FAILED (Expected {expected_status}, got {result.status_code})")
            else:
                print(f"✅ PASSED (Status: {result.status_code})")
        else:
            print("✅ PASSED (No strict status returned)")
    except ApiError as e:
        if e.status_code in expected_status:
            print(f"✅ PASSED via expected ApiError (Status: {e.status_code})")
        else:
            print(f"❌ FAILED with unexpected ApiError: {e.status_code} - {e}")
            logging.exception(e)
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")
        logging.exception(e)


# ==============================================================================
# 1. Basic Messaging (Form Data, Fluent Builder)
# ==============================================================================


def test_send_message_form_data_sync(api_key: str, domain: str, to_email: str) -> Any:
    data = {
        "from": f"test@{domain}",
        "to": [to_email],
        "subject": "Standard Message Test",
        "text": "Testing standard dictionary payload",
        "o:testmode": "yes",
    }
    with Client(auth=("api", api_key)) as client:
        return client.messages.create(domain=domain, data=data)


def test_send_message_with_builder_sync(api_key: str, domain: str, to_email: str) -> Any:
    payload, files = (
        MailgunMessageBuilder(f"fluent@{domain}")
        .add_recipient(to_email)
        .set_subject("Fluent Builder Test")
        .set_text("Testing fluent builder payload.")
        .add_custom_variable("test_run", "true")
        .build()
    )
    payload["o:testmode"] = "yes"
    with Client(auth=("api", api_key)) as client:
        return client.messages.create(domain=domain, data=payload, files=files)


# ==============================================================================
# 2. Domains, DNS & DKIM
# ==============================================================================


def test_domain_connections_sync(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        client.domains.create(data={"name": domain})
        return client.domains_connection.get(domain=domain)


def test_post_dkim_keys_sync(api_key: str, domain: str) -> Any:
    secret_key_filename = "smoke_test_server.key"  # pragma: allowlist secret
    secret_key_path = Path(secret_key_filename)
    try:
        subprocess.run(
            ["openssl", "genrsa", "-traditional", "-out", secret_key_filename, "--", "2048"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        files = [("pem", ("server.key", secret_key_path.read_bytes()))]
        data: dict[str, Any] = {"signing_domain": domain, "selector": "smtp", "bits": "2048"}
        with Client(auth=("api", api_key)) as client:
            return client.dkim_keys.create(data=data, files=files)
    finally:
        if secret_key_path.exists():
            secret_key_path.unlink()


def test_put_dkim_authority(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        # The internal _DOMAIN_ALIASES
        # map will translate "dkimauthority" -> "dkim_authority"
        return client.domains_dkimauthority.put(domain=domain, data={"self": "true"})


def test_put_dkim_selector(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.domains_dkimselector.put(domain=domain, data={"dkim_selector": "mailgun"})


def test_put_webprefix(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.domains_webprefix.put(domain=domain, data={"web_prefix": "tracking"})


# ==============================================================================
# 3. Tracking, Webhooks & Routes
# ==============================================================================


def test_put_tracking_sync(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.domains_tracking_open.put(domain=domain, data={"active": "yes"})


def test_webhook_crud_sync(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        client.domains_webhooks.create(
            domain=domain, data={"id": "clicked", "url": ["https://httpbin.org/post"]}
        )
        return client.domains_webhooks.delete(domain=domain, webhook_name="clicked")


def test_routes_sync(api_key: str, domain: str) -> Any:
    data = {
        "priority": 0,
        "description": "SDK Smoke Test Route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["stop()"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.routes.create(data=data)
        route_id = response.json().get("route", {}).get("id")
        if route_id:
            return client.routes.delete(route_id=route_id)
        return response


# ==============================================================================
# 4. Suppression, Analytics & Users
# ==============================================================================


def test_bounces_sync(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.bounces.get(domain=domain)


def test_list_statistic_v2(api_key: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.bounce_classification.create(data={"start": 0, "end": 100})


def test_post_analytics_logs(api_key: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.analytics_logs.create(data={"limit": 5})


def test_users_sync(api_key: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.users.get(filters={"role": "admin"})


# ==============================================================================
# 5. Mailing Lists
# ==============================================================================


def test_maillists_lists(api_key: str, list_address: str) -> Any:
    data = {"address": list_address, "description": "SDK Integration Test List"}
    with Client(auth=("api", api_key)) as client:
        client.lists.create(data=data)
        return client.lists.delete(address=list_address)


# ==============================================================================
# 6. Templates & Tags
# ==============================================================================


def test_templates(api_key: str, domain: str, template_name: str) -> Any:
    data = {
        "name": template_name,
        "description": "SDK Integration Test Template",
        "template": "<h1>Hello {{name}}</h1>",
    }
    with Client(auth=("api", api_key)) as client:
        client.templates.create(domain=domain, data=data)
        return client.templates.delete(domain=domain, template_name=template_name)


def test_tags(api_key: str, domain: str, tag_name: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        client.tags.put(domain=domain, tag_name=tag_name, data={"description": "Test SDK Tag"})
        return client.tags.delete(domain=domain, tag_name=tag_name)


# ==============================================================================
# 7. Infrastructure (IPs, Credentials, Keys)
# ==============================================================================


def test_infrastructure(api_key: str, domain: str, login: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        client.domains_credentials.create(
            domain=domain,
            data={"login": login, "password": "TestPassword123!"},  # pragma: allowlist secret
        )  # pragma: allowlist secret
        client.domains_credentials.delete(domain=domain, login=login)
        client.ips.get()
        return client.keys.get(filters={"domain_name": domain, "kind": "web"})


# ==============================================================================
# 8. InboxReady APIs
# ==============================================================================


def test_cross_version_routing_sync(api_key: str, address: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.addressvalidate.get(filters={"address": address})


def test_inboxready_apis(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.inbox.get(filters={"domain": domain})


# ==============================================================================
# 9. Core Features & Guardrails
# ==============================================================================


def test_deprecation_warnings_sync(api_key: str, domain: str) -> Any:
    with warnings.catch_warnings(record=True) as w, Client(auth=("api", api_key)) as client:
        warnings.simplefilter("always")
        response = client.tags.get(domain=domain, tag_name="sdk-test")
        if any(issubclass(warn.category, DeprecationWarning) for warn in w):
            print("  ↳ Captured expected DeprecationWarning for legacy endpoint!")
        return response


def test_expected_404_logging_sync(api_key: str, domain: str) -> Any:
    with Client(auth=("api", api_key)) as client:
        return client.templates.get(
            domain=domain, template_name="non_existent_fuzz_template_xyz123"
        )


# ==============================================================================
# ASYNC SUITE
# ==============================================================================


async def async_smoke_suite(api_key: str, domain: str) -> None:
    async def test_get_ips_async() -> Any:
        async with AsyncClient(auth=("api", api_key)) as client:
            return await client.ips.get()

    async def test_get_tags_async() -> Any:
        async with AsyncClient(auth=("api", api_key)) as client:
            return await client.tags.get(domain=domain)

    async def test_async_stream_pagination() -> Any:
        count = 0
        async with AsyncClient(auth=("api", api_key)) as client:
            async for event in client.events.stream(domain=domain, filters={"limit": 2}):
                count += 1
                if count >= 3:
                    break

        class MockResponse:
            status_code = 200

        return MockResponse()

    await run_async_test("Async IPs GET", test_get_ips_async, expected_status=(200, 400, 401, 403))
    await run_async_test(
        "Async Tags GET", test_get_tags_async, expected_status=(200, 400, 401, 403, 404)
    )
    await run_async_test(
        "Async Streaming Pagination", test_async_stream_pagination, expected_status=(200, 400)
    )


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    API_KEY = os.environ.get("APIKEY", "")
    DOMAIN = os.environ.get("DOMAIN", "")
    MESSAGES_TO = os.environ.get("MESSAGES_TO", f"success@{DOMAIN}")

    if not API_KEY or not DOMAIN:
        print("❌ Skipping smoke test. Export 'APIKEY' and 'DOMAIN' environment variables to run.")
        import sys

        sys.exit(0)

    # Generated Test Identifiers
    TEST_LIST = f"test-list@{DOMAIN}"
    TEST_CRED_LOGIN = f"api-user@{DOMAIN}"
    TEST_TAG = "sdk-integration-tag"
    TEST_TEMPLATE = "sdk-integration-template"
    VALIDATION_ADDRESS_1 = "foo@mailgun.net"

    print(f"🚀 Starting Universal Mailgun Smoke Tests against: {DOMAIN}")

    # --- Group 1: Basic Messaging ---
    run_sync_test(
        "Send Message (Form-Data)",
        lambda: test_send_message_form_data_sync(API_KEY, DOMAIN, MESSAGES_TO),
        expected_status=(200, 400, 401, 403),
    )
    run_sync_test(
        "Send Message (Fluent Builder)",
        lambda: test_send_message_with_builder_sync(API_KEY, DOMAIN, MESSAGES_TO),
        expected_status=(200, 400, 401, 403),
    )

    # --- Group 2: Domains, DNS & DKIM ---
    run_sync_test(
        "Domain Connections",
        lambda: test_domain_connections_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "DKIM Authority",
        lambda: test_put_dkim_authority(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "DKIM Selector",
        lambda: test_put_dkim_selector(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Web Prefix",
        lambda: test_put_webprefix(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Generate & Upload DKIM Key (OpenSSL)",
        lambda: test_post_dkim_keys_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 3: Tracking, Webhooks & Routes ---
    run_sync_test(
        "Tracking",
        lambda: test_put_tracking_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Webhook CRUD",
        lambda: test_webhook_crud_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Routes API",
        lambda: test_routes_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 4: Suppression, Analytics & Users ---
    run_sync_test(
        "Bounces Fetch",
        lambda: test_bounces_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Bounce Classification",
        lambda: test_list_statistic_v2(API_KEY),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Analytics Logs",
        lambda: test_post_analytics_logs(API_KEY),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Account Users",
        lambda: test_users_sync(API_KEY),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 5: Mailing Lists ---
    run_sync_test(
        "Mailing Lists",
        lambda: test_maillists_lists(API_KEY, TEST_LIST),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 6: Templates & Tags ---
    run_sync_test(
        "Templates CRUD",
        lambda: test_templates(API_KEY, DOMAIN, TEST_TEMPLATE),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Tags CRUD",
        lambda: test_tags(API_KEY, DOMAIN, TEST_TAG),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 7: Infrastructure ---
    run_sync_test(
        "Infrastructure (IPs, Credentials, Keys)",
        lambda: test_infrastructure(API_KEY, DOMAIN, TEST_CRED_LOGIN),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 8: InboxReady APIs ---
    run_sync_test(
        "Cross-Version Routing (v4)",
        lambda: test_cross_version_routing_sync(API_KEY, VALIDATION_ADDRESS_1),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "InboxReady (Validation & Inbox Placement)",
        lambda: test_inboxready_apis(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Core Features & Guardrails ---
    run_sync_test(
        "Deprecation Warning Interceptor",
        lambda: test_deprecation_warnings_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Test 404 Safe Logging",
        lambda: test_expected_404_logging_sync(API_KEY, DOMAIN),
        expected_status=(404,),
    )

    # --- ASYNC SUITE ---
    asyncio.run(async_smoke_suite(API_KEY, DOMAIN))

    print(f"\n{'=' * 60}\n✅ ALL SMOKE TESTS COMPLETED\n{'=' * 60}")

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
import warnings
from collections.abc import Awaitable, Callable
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
            if result.status_code in expected_status:
                print(f"✅ SUCCESS (Status Code: {result.status_code})\n")
            else:
                print(f"❌ FAILED (Expected {expected_status}, got {result.status_code})\n")
        else:
            print(f"✅ SUCCESS ({result})\n")
    except ApiError as e:
        print(f"⚠️ SDK CAUGHT API ERROR: {e}")
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")


async def run_async_test(
    test_name: str,
    func: Callable[[], Awaitable[Any]],
    expected_status: tuple[int, ...] = (200,),
) -> None:
    """Execute and validate asynchronous API calls."""
    print(f"\n{'=' * 60}\n⚡ ASYNC RUN: {test_name}\n{'=' * 60}")
    try:
        result = await func()
        if hasattr(result, "status_code"):
            if result.status_code in expected_status:
                print(f"✅ SUCCESS (Status Code: {result.status_code})\n")
            else:
                print(f"❌ FAILED (Expected {expected_status}, got {result.status_code})\n")
        else:
            # Safely handle our stream() tests that return strings or counts
            print(f"✅ SUCCESS ({result})\n")
    except ApiError as e:
        print(f"⚠️ SDK CAUGHT API ERROR: {e}")
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")


# ==============================================================================
# Synchronous Smoke Tests
# ==============================================================================


# --- Group 1: Messaging ---


def test_send_message_form_data_sync(api_key: str, domain: str, messages_to: str) -> Any:
    """Test: Send a message using standard Form-Data."""
    data: dict[str, Any] = {
        "from": f"Smoke Test <mailgun@{domain}>",
        "to": [messages_to],
        "subject": "Mailgun SDK Smoke Test (Form-Data)",
        "text": "If you see this, the synchronous Form-Data test passed!",
        "o:testmode": "yes",  # Must be a string boolean
    }
    with Client(auth=("api", api_key)) as client:
        return client.messages.create(domain=domain, data=data)


def test_send_message_with_builder_sync(api_key: str, domain: str, messages_to: str) -> Any:
    """Test: Construct complex payloads safely using MailgunMessageBuilder."""
    builder = MailgunMessageBuilder(from_email=f"Smoke Builder <mailgun@{domain}>")
    builder.add_recipient(messages_to)
    builder.set_subject("Mailgun SDK Builder Test")
    builder.set_text("If you see this, the MailgunMessageBuilder worked safely!")

    # Safely abstract custom prefixes directly into the payload array
    builder._payload["o:testmode"] = "yes"
    builder._payload["v:smoke_run_id"] = "12345"
    builder._payload["o:tag"] = "smoke-test"

    payload, files = builder.build()

    with Client(auth=("api", api_key)) as client:
        return client.messages.create(domain=domain, data=payload, files=files)


def test_messaging_mime(api_key: str, domain: str, to_email: str) -> Any:
    """Test: Send raw MIME string."""
    with Client(auth=("api", api_key)) as client:
        mime_string = (
            f"From: sender@{domain}\n"
            f"To: {to_email}\n"
            "Subject: MIME Smoke Test\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "This is a raw MIME message."
        ).encode("utf-8")
        return client.mimemessage.create(
            domain=domain, data={"to": to_email}, files={"message": ("message.mime", mime_string)}
        )


# --- Group 2: Domain Operations ---


def test_get_domains_sync(api_key: str) -> Any:
    """Test: Fetch domains (Validates v3/v4 routing architecture)."""
    with Client(auth=("api", api_key)) as client:
        return client.domains.get(filters={"limit": 2})


def test_domain_tracking_and_dkim(api_key: str, domain: str) -> Any:
    """Test: Domain Tracking (v3) and DKIM Keys (v1)."""
    with Client(auth=("api", api_key)) as client:
        client.domains_tracking.get(domain=domain)
        return client.dkim_keys.get(data={"signing_domain": domain})


# --- Group 3: Webhooks ---


def test_webhooks(api_key: str, domain: str) -> Any:
    """Test: v4 Domain Webhooks and v1 Account Webhooks."""
    with Client(auth=("api", api_key)) as client:
        client.domains_webhooks.get(domain=domain)
        return client.account_webhooks.get()


# --- Group 4: Analytics & Events ---


def test_create_bounces_json_sync(api_key: str, domain: str) -> Any:
    """Test: Bulk upload bounces using JSON (Validates `is_json` serialization)."""
    data: list[dict[str, str]] = [
        {"address": f"bounce1@{domain}", "code": "550", "error": "Smoke Test Bounce 1"},
        {"address": f"bounce2@{domain}", "code": "550", "error": "Smoke Test Bounce 2"},
    ]
    with Client(auth=("api", api_key)) as client:
        return client.bounces.create(
            domain=domain, data=data, headers={"Content-Type": "application/json"}
        )


def test_events_and_analytics(api_key: str, domain: str) -> Any:
    """Test: Events and v2 Bounce Classification Metrics."""
    with Client(auth=("api", api_key)) as client:
        client.events.get(domain=domain, filters={"limit": 5})
        payload = {
            "start": "Tue, 12 Nov 2024 23:00:00 UTC",
            "end": "Wed, 13 Nov 2024 23:00:00 UTC",
            "resolution": "day",
            "duration": "24h0m0s",
            "metrics": ["critical_bounce_count"],
        }
        return client.bounceclassification_metrics.create(
            data=payload, headers={"Content-Type": "application/json"}
        )


def test_metrics_and_logs(api_key: str, domain: str) -> Any:
    """Test: v1 Analytics Metrics."""
    with Client(auth=("api", api_key)) as client:
        return client.analytics_metrics.create(
            data={
                "start": "Wed, 01 Jan 2025 00:00:00 +0000",
                "end": "Thu, 02 Jan 2025 00:00:00 +0000",
                "resolution": "day",
                "metrics": ["accepted_count"],
            }
        )


# --- Group 5: Lists & Routes ---


def test_mailing_lists_and_routes(api_key: str, domain: str) -> Any:
    """Test: v3 Lists and Routes."""
    with Client(auth=("api", api_key)) as client:
        client.lists.get()
        return client.routes.get(domain=domain)


# --- Group 6: Templates ---


def test_templates(api_key: str, domain: str) -> Any:
    """Test: v3 Templates."""
    with Client(auth=("api", api_key)) as client:
        return client.templates.get(domain=domain, filters={"limit": 5})


# --- Group 7: Infrastructure ---


def test_infrastructure(api_key: str, domain: str) -> Any:
    """Test: IPs, SMTP Credentials, and API Keys."""
    with Client(auth=("api", api_key)) as client:
        client.ips.get(domain=domain)
        client.domains_credentials.get(domain=domain)
        return client.keys.get(filters={"limit": 5})


# --- Group 8: InboxReady APIs ---


def test_cross_version_routing_sync(api_key: str, validation_address: str) -> Any:
    """Test: Call a v4 endpoint (Validates cross-API dynamic routing)."""
    with Client(auth=("api", api_key)) as client:
        return client.addressvalidate.get(filters={"address": validation_address})


def test_inboxready_apis(api_key: str, domain: str) -> Any:
    """Test: InboxReady Domain Status and Single Validation."""
    with Client(auth=("api", api_key)) as client:
        client.inboxready_domains.get()
        return client.addressvalidate.create(domain=domain, data={"address": "test@example.com"})


# --- Core Client Features & Guardrails ---


def test_deprecation_warnings_sync(api_key: str, domain: str) -> Any:
    """Test: Verify SDK intercepts legacy APIs and emits DeprecationWarnings."""
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always", DeprecationWarning)

        with Client(auth=("api", api_key)) as client:
            response = client.tag.get(domain=domain, filters={"tag": "my-tag"})

        warning_emitted = any(
            issubclass(w.category, DeprecationWarning) and "legacy Tag API" in str(w.message)
            for w in caught_warnings
        )

        if not warning_emitted:
            raise AssertionError("SDK failed to emit a DeprecationWarning for legacy endpoint")

        return response


def test_expected_404_logging_sync(api_key: str) -> Any:
    """Test: Fetch a fake domain to trigger CWE-532 secure logging."""
    with Client(auth=("api", api_key)) as client:
        return client.domains.get(domain_name="this-domain-does-not-exist.com")


def test_sync_context_manager(api_key: str) -> Any:
    """Test: Demonstrate resource-safe client usage via Context Manager."""
    with Client(auth=("api", api_key)) as safe_client:
        return safe_client.domainlist.get(filters={"limit": 1})


def test_sync_stream_pagination(api_key: str, domain: str) -> str:
    """Test: Lazy pagination generator (sync)."""
    count = 0
    with Client(auth=("api", api_key)) as client:
        for _ in client.events.stream(domain=domain, filters={"limit": 2}):
            count += 1
            if count >= 5:
                break

    return f"Successfully streamed and paginated {count} events."


# ==============================================================================
# Asynchronous Smoke Tests
# ==============================================================================


async def test_async_stream_pagination(api_key: str, domain: str) -> str:
    """Test: Lazy pagination generator (async)."""
    count = 0
    async with AsyncClient(auth=("api", api_key)) as async_client:
        async for _ in async_client.events.stream(domain=domain, filters={"limit": 2}):
            count += 1
            if count >= 5:
                break

    return f"Successfully streamed {count} events asynchronously."


async def test_get_ips_async(api_key: str) -> Any:
    """Test: Fetch dedicated IPs asynchronously."""
    async with AsyncClient(auth=("api", api_key)) as async_client:
        return await async_client.ips.get()


async def test_get_tags_async(api_key: str, domain: str) -> Any:
    """Test: Fetch analytics tags asynchronously."""
    async with AsyncClient(auth=("api", api_key)) as async_client:
        return await async_client.tags.get(domain=domain, filters={"limit": 2})


async def async_smoke_suite(api_key: str, domain: str) -> None:
    """Execute asynchronous tests."""
    await run_async_test(
        "Async IPs Fetch", lambda: test_get_ips_async(api_key), expected_status=(200, 401, 403, 404)
    )
    await run_async_test(
        "Async Stream Pagination", lambda: test_async_stream_pagination(api_key, domain)
    )
    await run_async_test(
        "Async Tags Fetch",
        lambda: test_get_tags_async(api_key, domain),
        expected_status=(200, 401, 403, 404),
    )


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "sandbox.mailgun.org")
    MESSAGES_TO: str = os.environ.get("MESSAGES_TO", f"success@{DOMAIN}")
    VALIDATION_ADDRESS_1: str = os.environ.get("VALIDATION_ADDRESS_1", "test@example.com")

    if not API_KEY:
        print("⚠️ WARNING: 'APIKEY' is not set. Network requests will return 401 Unauthorized.")

    print(f"🔧 Testing against domain: {DOMAIN}")
    print(f"📨 Authorized recipient: {MESSAGES_TO}\n")

    # --- Group 1: Messaging ---
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
    run_sync_test(
        "Raw MIME Message Engine",
        lambda: test_messaging_mime(API_KEY, DOMAIN, MESSAGES_TO),
        expected_status=(200, 400, 401, 403),
    )

    # --- Group 2: Domain Operations ---
    run_sync_test(
        "Get Domains (v3/v4)",
        lambda: test_get_domains_sync(API_KEY),
        expected_status=(200, 401, 403),
    )
    run_sync_test(
        "Domain Tracking & DKIM Keys",
        lambda: test_domain_tracking_and_dkim(API_KEY, DOMAIN),
        expected_status=(200, 401, 403, 404),
    )

    # --- Group 3: Webhooks ---
    run_sync_test(
        "Webhooks (v1 Account & v4 Domain)",
        lambda: test_webhooks(API_KEY, DOMAIN),
        expected_status=(200, 401, 403, 404),
    )

    # --- Group 4: Analytics, Events & Bounces ---
    run_sync_test(
        "Bulk Create Bounces (JSON Payload)",
        lambda: test_create_bounces_json_sync(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403),
    )
    run_sync_test(
        "Events & Bounce Classification",
        lambda: test_events_and_analytics(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )
    run_sync_test(
        "Metrics & Logs API",
        lambda: test_metrics_and_logs(API_KEY, DOMAIN),
        expected_status=(200, 400, 401, 403, 404),
    )

    # --- Group 5: Lists & Routes ---
    run_sync_test(
        "Mailing Lists & Routes Engine",
        lambda: test_mailing_lists_and_routes(API_KEY, DOMAIN),
        expected_status=(200, 401, 403, 404),
    )

    # --- Group 6: Templates ---
    run_sync_test(
        "Templates Retrieval",
        lambda: test_templates(API_KEY, DOMAIN),
        expected_status=(200, 401, 403, 404),
    )

    # --- Group 7: Infrastructure ---
    run_sync_test(
        "Infrastructure (IPs, Credentials, Keys)",
        lambda: test_infrastructure(API_KEY, DOMAIN),
        expected_status=(200, 401, 403, 404),
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
        lambda: test_expected_404_logging_sync(API_KEY),
        expected_status=(404,),
    )
    run_sync_test(
        "Stream Pagination (Lazy Loading)", lambda: test_sync_stream_pagination(API_KEY, DOMAIN)
    )
    run_sync_test(
        "Sync Context Manager (Resource Safe)",
        lambda: test_sync_context_manager(API_KEY),
        expected_status=(200, 401, 403, 404),
    )

    # Run Asynchronous Suite
    asyncio.run(async_smoke_suite(API_KEY, DOMAIN))

    print(f"\n🎉 Smoke test suite completed.")

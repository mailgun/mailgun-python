"""
Ultimate Smoke Test for Mailgun Python SDK.

This script serves as both an integration verification tool and
executable documentation for developers. It tests synchronous and
asynchronous clients, standard Form-Data requests, JSON payloads,
and error handling.

Usage:
    export APIKEY="your-api-key"  # pragma: allowlist secret
    export DOMAIN="your-sandbox-or-real-domain.mailgun.org"
    export MESSAGES_TO="your.verified@email.com"
    python mailgun/examples/smoke_test.py
"""

import asyncio
import logging
import os
import warnings
from collections.abc import Awaitable, Callable
from typing import Any

from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import ApiError

# Enable SDK logging to demonstrate the new CWE-532 secure error logging
logging.getLogger("mailgun.client").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# Environment setup
API_KEY = os.environ.get("APIKEY", "")
DOMAIN = os.environ.get("DOMAIN", "sandbox.mailgun.org")
MESSAGES_TO = os.environ.get("MESSAGES_TO", f"success@{DOMAIN}")


# Initialize clients
sync_client = Client(auth=("api", API_KEY))


def run_sync_test(
    test_name: str, func: Callable[[], Any], expected_status: tuple[int, ...] = (200,)
) -> None:
    """Wrapper to execute and validate synchronous API calls."""
    print(f"\n{'=' * 60}\n🚀 SYNC RUN: {test_name}\n{'=' * 60}")
    try:
        result = func()
        if getattr(result, "status_code", None) in expected_status:
            print(f"✅ SUCCESS (Status Code: {result.status_code})")
        else:
            print(
                f"❌ FAILED (Expected {expected_status}, got {getattr(result, 'status_code', 'None')})"
            )
    except ApiError as e:
        print(f"⚠️ SDK CAUGHT API ERROR: {e}")
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")


async def run_async_test(
    test_name: str, func: Callable[[], Awaitable[Any]], expected_status: tuple[int, ...] = (200,)
) -> None:
    """Wrapper to execute and validate asynchronous API calls."""
    print(f"\n{'=' * 60}\n⚡ ASYNC RUN: {test_name}\n{'=' * 60}")
    try:
        result = await func()
        if getattr(result, "status_code", None) in expected_status:
            print(f"✅ SUCCESS (Status Code: {result.status_code})")
        else:
            print(
                f"❌ FAILED (Expected {expected_status}, got {getattr(result, 'status_code', 'None')})"
            )
    except ApiError as e:
        print(f"⚠️ SDK CAUGHT API ERROR: {e}")
    except Exception as e:
        print(f"💥 FATAL UNEXPECTED ERROR: {e}")


# --- SYNC TESTS ---


def test_get_domains() -> Any:
    """Test 1: Fetch domains (Validates v3/v4 routing architecture)."""
    return sync_client.domains.get(filters={"limit": 2})


def test_send_message_form_data() -> Any:
    """Test 2: Send a message using standard Form-Data."""
    data = {
        "from": f"Smoke Test <mailgun@{DOMAIN}>",
        "to": [MESSAGES_TO],
        "subject": "Mailgun SDK Smoke Test (Form-Data)",
        "text": "If you see this, the synchronous Form-Data test passed!",
        "o:testmode": True,  # Don't actually send the email
    }
    return sync_client.messages.create(domain=DOMAIN, data=data)


def test_create_bounces_json() -> Any:
    """Test 3: Bulk upload bounces using JSON (Validates our new `is_json` serialization)."""
    # Mailgun /lists doesn't support JSON. /bounces bulk upload DOES support JSON arrays!
    data = [
        {"address": f"bounce1@{DOMAIN}", "code": "550", "error": "Smoke Test Bounce 1"},
        {"address": f"bounce2@{DOMAIN}", "code": "550", "error": "Smoke Test Bounce 2"},
    ]
    return sync_client.bounces.create(
        domain=DOMAIN, data=data, headers={"Content-Type": "application/json"}
    )


def test_expected_404_logging() -> Any:
    """Test 4: Fetch a fake domain to trigger CWE-532 secure logging."""
    return sync_client.domains.get(domain_name="this-domain-does-not-exist.com")


def test_cross_version_routing() -> Any:
    """Test 5: Call a v4 endpoint (Validates cross-API dynamic routing)."""
    # Using addressvalidate (/v4/address/validate).
    # Returns 403 on Free plans, 200 on Paid plans. Both prove successful URL routing.
    return sync_client.addressvalidate.get(address="test@example.com")


# --- DEPRECATION WARNING TESTS ---


def test_deprecation_warnings() -> Any:
    """Test 6: Verify SDK intercepts legacy APIs and emits DeprecationWarnings."""
    with warnings.catch_warnings(record=True) as caught_warnings:
        # Force Python to capture all DeprecationWarnings
        warnings.simplefilter("always", DeprecationWarning)

        # Trigger the legacy Tag API (client.tag instead of client.tags)
        # We don't care if it returns 200 or 404, we only care about the warning.
        response = sync_client.tag.get(domain=DOMAIN)

        # Validate that our SDK Interceptor successfully fired the warning
        warning_emitted = any(
            issubclass(w.category, DeprecationWarning) and "legacy Tag API" in str(w.message)
            for w in caught_warnings
        )

        if not warning_emitted:
            raise AssertionError("SDK failed to emit a DeprecationWarning for a legacy endpoint!")

        return response


# --- ASYNC TESTS ---


async def async_smoke_suite() -> None:
    """Execute asynchronous tests using the AsyncClient context manager."""
    async with AsyncClient(auth=("api", API_KEY)) as async_client:

        async def test_get_tags() -> Any:
            """Test 5: Fetch analytics tags asynchronously."""
            return await async_client.tags.get(domain=DOMAIN, filters={"limit": 2})

        async def test_get_ips() -> Any:
            """Test 6: Fetch dedicated IPs asynchronously."""
            return await async_client.ips.get()

        await run_async_test("Async Tags Fetch", test_get_tags)
        await run_async_test("Async IPs Fetch", test_get_ips)


if __name__ == "__main__":
    if not API_KEY:
        print(
            "⚠️ WARNING: 'MAILGUN_API_KEY' is not set. Network requests will return 401 Unauthorized."
        )

    print(f"🔧 Testing against domain: {DOMAIN}")
    print(f"📨 Authorized recipient: {MESSAGES_TO}\n")

    # Run Synchronous Suite
    run_sync_test("Get Domains (v3/v4)", test_get_domains)
    run_sync_test("Send Message (Form-Data)", test_send_message_form_data)
    run_sync_test("Bulk Create Bounces (JSON Payload)", test_create_bounces_json)
    run_sync_test("Test 404 Safe Logging", test_expected_404_logging, expected_status=(404,))
    run_sync_test(
        "Cross-Version Routing (v4)", test_cross_version_routing, expected_status=(200, 403)
    )
    run_sync_test(
        "Deprecation Warning Interceptor",
        test_deprecation_warnings,
        expected_status=(200, 400, 404),
    )
    # Run Asynchronous Suite
    asyncio.run(async_smoke_suite())

    print(f"\n🎉 Smoke test suite completed.")

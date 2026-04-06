"""Live meta-tests to intelligently verify URL routing against Mailgun servers."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import pytest

from mailgun.client import Client
from mailgun.handlers.error_handler import ApiError


@pytest.fixture(scope="module")
def live_setup() -> tuple[Client, str]:
    """Initialize the client with real environment variables."""
    # Use empty string fallback to guarantee 'str' type for Pyright strict mode
    api_key = os.environ.get("APIKEY", "")
    domain = os.environ.get("DOMAIN", "")

    if not api_key or not domain:
        pytest.skip("APIKEY or DOMAIN environment variables not set.")

    client = Client(auth=("api", api_key))
    return client, domain


def test_intelligent_routing_to_mailgun_servers(live_setup: tuple[Client, str]) -> None:
    """Verify that endpoints chain correctly to valid Mailgun HTTP routes."""
    client, domain = live_setup

    # ВКАЗУЄМО ТИП ДЛЯ MYPY: Словник з ключами str та значеннями-функціями, які не приймають аргументів і повертають Any.
    TEST_CALLS: dict[str, Callable[[], Any]] = {
        "accounts": lambda: client.accounts_subaccounts.get(),
        "addressvalidate": lambda: client.addressvalidate.get(address="test@example.com"),
        "alerts": lambda: client.alerts_events.get(),
        "analytics": lambda: client.analytics.get(),
        "bounces": lambda: client.bounces.get(domain=domain),
        "bounce_classification": lambda: client.bounce_classification.create(data={"list": "test"}),
        "complaints": lambda: client.complaints.get(domain=domain),
        "dkim": lambda: client.dkim.get(),
        "domainlist": lambda: client.domainlist.get(),
        "domains_credentials": lambda: client.domains_credentials.get(domain=domain),
        "events": lambda: client.events.get(domain=domain),
        "inboxready": lambda: client.inboxready_domains.get(),
        "inspect": lambda: client.inspect_analyze.get(),
        "ippools": lambda: client.ippools.get(),
        "ips": lambda: client.ips.get(),
        "keys": lambda: client.keys.get(),
        "lists": lambda: client.lists.get(),
        "messages": lambda: client.messages.create(domain=domain, data={"from": "test@example.com"}),
        "mimemessage": lambda: client.mimemessage.create(domain=domain, data={"from": "test@example.com"}),
        "preview": lambda: client.preview_tests_clients.get(),
        "reputationanalytics": lambda: client.reputationanalytics_gpt_domains.get(),
        "routes": lambda: client.routes.get(),
        "subaccount_ip_pools": lambda: client.subaccount_ip_pools.get(),
        "tags": lambda: client.tags.get(domain=domain),
        "templates": lambda: client.templates.get(domain=domain),
        "unsubscribes": lambda: client.unsubscribes.get(domain=domain),
        "users": lambda: client.users.get(),
        "webhooks": lambda: client.webhooks.get(domain=domain),
        "whitelists": lambda: client.whitelists.get(domain=domain),
        "x509": lambda: client.x509_status.get(domain=domain),
    }

    routing_crashes = []

    print("\n" + "=" * 80)
    print(f"🚀 STARTING INTELLIGENT LIVE ROUTING TEST (Domain: {domain})")
    print("=" * 80)

    for ep_name, caller in sorted(TEST_CALLS.items()):
        try:
            response = caller()
            status = getattr(response, "status_code", "UNKNOWN")
            url = getattr(response, "url", "UNKNOWN_URL")

            if status == 404 and ep_name in ("x509", "analytics"):
                status_marker = f"✅ HTTP {status} (Expected)"
            elif status == 404:
                status_marker = f"❌ HTTP {status} (Bad Route?)"
                routing_crashes.append((ep_name, url))
            else:
                status_marker = f"✅ HTTP {status}"

            print(f"{status_marker:<20} | {ep_name:<20} -> {url}")
            time.sleep(0.3)

        except ApiError as e:
            print(f"⚠️ [SDK ERROR]        | {ep_name:<20} -> {e}")
        except Exception as e:
            print(f"💥 [CRASH]            | {ep_name:<20} -> Python Exception: {e}")
            routing_crashes.append((ep_name, str(e)))

    print("=" * 80)
    assert len(routing_crashes) == 0, f"Python SDK crashed for {len(routing_crashes)} endpoints: {routing_crashes}"

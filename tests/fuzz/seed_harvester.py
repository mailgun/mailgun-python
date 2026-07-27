#!/usr/bin/env python3
"""Mailgun Enhanced Fuzzer Seed Harvester
Harvests successful AND error-case payloads to seed the fuzzing corpus.
"""

import json
import os
from pathlib import Path
from typing import Any

import requests


# Ensure configuration is robust
API_KEY = os.environ.get("APIKEY")
DOMAIN = os.environ.get("DOMAIN", "sandbox-fuzz.mailgun.org")

# Schema-aware targets based on Mailgun API documentation
TARGETS: list[dict[str, Any]] = [
    {
        "method": "GET",
        "name": "bounces_get",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/bounces",
    },
    {
        "data": {"from": "fuzz@example.com", "subject": "fuzz", "to": "bad-address"},
        "method": "POST",
        "name": "messages_post",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/messages",
    },
    {
        "method": "GET",
        "name": "routes_get",
        "url": "https://api.mailgun.net/v3/routes",
    },
    {
        "method": "GET",
        "name": "validate_get",
        "params": {"address": "test@example.com"},
        "url": "https://api.mailgun.net/v4/address/validate",
    },
    # NEW ENDPOINTS ADDED BELOW
    {
        "method": "GET",
        "name": "webhooks_get",
        "url": f"https://api.mailgun.net/v3/domains/{DOMAIN}/webhooks",
    },
    {
        "method": "GET",
        "name": "domains_get",
        "url": "https://api.mailgun.net/v4/domains",
    },
    {
        "method": "GET",
        "name": "events_get",
        "params": {"limit": 5},
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/events",
    },
    {
        "method": "GET",
        "name": "lists_get",
        "url": "https://api.mailgun.net/v3/lists",
    },
    {
        "method": "GET",
        "name": "templates_get",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/templates",
    },
    {
        "method": "GET",
        "name": "ips_get",
        "url": "https://api.mailgun.net/v3/ips",
    },
    {
        "method": "GET",
        "name": "ip_pools_get",
        "url": "https://api.mailgun.net/v3/ip_pools",
    },
    {
        "method": "GET",
        "name": "stats_get",
        "params": {"event": ["accepted", "delivered", "failed"]},
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/stats/total",
    }
]

# Map specific API targets to their respective fuzzer corpus directories
CORPUS_MAP: dict[str, list[str]] = {
    "fuzz_handlers": [
        "bounces_get", "routes_get", "webhooks_get", "domains_get",
        "lists_get", "templates_get", "ips_get", "ip_pools_get", "stats_get"
    ],
    "fuzz_async_client": [
        "messages_post", "events_get", "validate_get", "domains_get"
    ],
    "fuzz_error_parser": [
        # Allows the error parser to learn from any 400/401/404 payloads returned
        "messages_post", "validate_get", "templates_get"
    ]
}

def harvest_seeds() -> None:
    if not API_KEY:
        print("❌ Error: APIKEY environment variable is missing.")
        return

    auth = ("api", API_KEY)

    for target in TARGETS:
        method = target.get("method", "GET")
        url = target["url"]
        print(f"📡 Harvesting {method} {url}...")

        try:
            # Capture data to force various API responses (Success vs Error)
            if method == "POST":
                resp = requests.post(
                    url, auth=auth, data=target.get("data"), timeout=10
                )
            else:
                resp = requests.get(
                    url, auth=auth, params=target.get("params"), timeout=10
                )

            # Save the raw JSON payload
            # We save the status code in the filename so the fuzzer learns
            # to distinguish between success and error schemas
            try:
                parsed_json = resp.json()
            except ValueError:
                print(f"  ⚠️ Warning: Non-JSON response for {target['name']} (HTTP {resp.status_code})")
                parsed_json = {"raw_text": resp.text}

            payload = json.dumps(parsed_json, indent=2).encode("utf-8")

            for folder, target_names in CORPUS_MAP.items():
                if target["name"] in target_names:
                    dir_path = Path("tests") / "fuzz" / "corpus" / folder
                    dir_path.mkdir(parents=True, exist_ok=True)

                    filename = f"{resp.status_code}_{target['name']}.json"
                    file_path = dir_path / filename
                    file_path.write_bytes(payload)

                    print(f"  ✅ Saved {filename} to {folder}")

        except Exception as e:  # noqa: BLE001
            print(f"  ❌ Failed {target['name']}: {e}")

if __name__ == "__main__":
    harvest_seeds()

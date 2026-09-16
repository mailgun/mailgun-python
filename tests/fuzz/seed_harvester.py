#!/usr/bin/env python3
"""Mailgun Enhanced Fuzzer Seed Harvester.

Harvests realistic payloads from live API or generates high-entropy offline
synthetic seeds for each fuzzer corpus directory to bootstrap libFuzzer.
"""

import json
import os
from pathlib import Path
from typing import Any

# Domain and API key configuration
API_KEY = os.environ.get("APIKEY")
DOMAIN = os.environ.get("DOMAIN", "sandbox-fuzz.mailgun.org")

TARGETS: list[dict[str, Any]] = [
    {
        "name": "messages_post",
        "method": "POST",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/messages",
        "data": {
            "from": f"fuzz@{DOMAIN}",
            "to": "test@example.com",
            "subject": "Fuzz Seed Email",
            "text": "Hello world from fuzzer seed harvester",
            "o:tag": "fuzz-seed",
            "o:tracking": "yes",
        },
    },
    {
        "name": "bounces_get",
        "method": "GET",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/bounces",
        "params": {"limit": 5},
    },
    {
        "name": "domains_get",
        "method": "GET",
        "url": "https://api.mailgun.net/v4/domains",
        "params": {"limit": 10},
    },
    {
        "name": "events_get",
        "method": "GET",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/events",
        "params": {"limit": 10, "ascending": "yes"},
    },
    {
        "name": "webhooks_get",
        "method": "GET",
        "url": f"https://api.mailgun.net/v3/domains/{DOMAIN}/webhooks",
    },
    {
        "name": "validate_get",
        "method": "GET",
        "url": "https://api.mailgun.net/v4/address/validate",
        "params": {"address": "fuzz.deliverability@gmail.com"},
    },
    {
        "name": "templates_get",
        "method": "GET",
        "url": f"https://api.mailgun.net/v3/{DOMAIN}/templates",
        "params": {"limit": 5},
    },
    {
        "name": "ips_get",
        "method": "GET",
        "url": "https://api.mailgun.net/v3/ips",
    },
    {
        "name": "routes_get",
        "method": "GET",
        "url": "https://api.mailgun.net/v3/routes",
        "params": {"limit": 5},
    },
]

CORPUS_MAP: dict[str, list[str]] = {
    "fuzz_handlers": [
        "bounces_get",
        "domains_get",
        "events_get",
        "ips_get",
        "messages_post",
        "routes_get",
        "templates_get",
        "validate_get",
        "webhooks_get",
    ],
    "fuzz_async_client": ["messages_post", "events_get", "domains_get"],
    "fuzz_error_parser": ["messages_post", "validate_get", "templates_get"],
    "fuzz_structure_aware": ["domains_get", "webhooks_get", "messages_post"],
    "fuzz_semantic_payloads": ["messages_post"],
}

_SYNTHETIC_SEEDS: dict[str, list[dict[str, Any]]] = {
    "messages_post": [
        {
            "from": "Admin <admin@example.com>",
            "to": ["user1@example.com", "user2@example.com"],
            "subject": "Seed Subject with Variables",
            "text": "Hello %recipient.name%",
            "recipient-variables": '{"user1@example.com": {"name": "Alice"}}',
            "o:tag": ["newsletter", "fuzz"],
            "o:tracking": True,
            "o:deliverytime": "Fri, 25 Oct 2026 23:10:10 -0000",
        },
        {
            "from": "spoofed@evil.com\r\nBcc: victim@target.com",
            "to": "test@[127.0.0.1]",
            "subject": "CRLF Injection Probe",
            "text": "Payload test",
        },
    ],
    "events_get": [
        {
            "items": [
                {
                    "event": "delivered",
                    "id": "A_EV_12345",
                    "timestamp": 1714000000.0,
                    "recipient": "user@example.com",
                }
            ],
            "paging": {
                "next": "https://api.mailgun.net/v3/events?page=eyJwIjoxfQ==&limit=10",
                "previous": "https://api.mailgun.net/v3/events?page=eyJwIjowfQ==",
            },
        }
    ],
    "webhooks_get": [
        {
            "webhook": {
                "url": "https://example.com/webhook",
                "urls": ["https://example.com/webhook"],
            }
        }
    ],
    "validate_get": [
        {
            "address": "test@example.com",
            "is_valid": True,
            "parts": {"domain": "example.com", "local_part": "test"},
            "risk": "low",
        }
    ],
}


def _save_corpus_payload(target_name: str, payload_bytes: bytes, prefix: str) -> None:
    """Saves generated or harvested payload into mapped corpus directories."""
    for folder, mapped_targets in CORPUS_MAP.items():
        if target_name in mapped_targets:
            dest_dir = Path("tests") / "fuzz" / "corpus" / folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{prefix}_{target_name}.json"
            file_path = dest_dir / filename
            file_path.write_bytes(payload_bytes)
            print(f"  [SAVED] {file_path}")


def harvest_seeds() -> None:
    """Main execution router: queries live endpoints if API_KEY is set, else synthesizes."""
    if not API_KEY:
        print("[INFO] No APIKEY provided. Generating high-entropy offline synthetic seeds...")
        for target_name, seed_list in _SYNTHETIC_SEEDS.items():
            for idx, seed_obj in enumerate(seed_list):
                payload_bytes = json.dumps(seed_obj, indent=2).encode("utf-8")
                _save_corpus_payload(target_name, payload_bytes, prefix=f"synthetic_{idx}")
        print("[SUCCESS] Synthetic seed generation complete.")
        return

    import requests

    auth = ("api", API_KEY)
    print(f"[INFO] Harvesting live seeds using API key against domain: {DOMAIN}")

    for target in TARGETS:
        method = target.get("method", "GET")
        url = target["url"]
        print(f"📡 Querying {method} {url}...")

        try:
            if method == "POST":
                resp = requests.post(url, auth=auth, data=target.get("data"), timeout=8)
            else:
                resp = requests.get(url, auth=auth, params=target.get("params"), timeout=8)

            try:
                data = resp.json()
            except ValueError:
                data = {"raw_content": resp.text}

            payload_bytes = json.dumps(data, indent=2).encode("utf-8")
            _save_corpus_payload(target["name"], payload_bytes, prefix=f"http_{resp.status_code}")

        except Exception as e:
            print(f"  [WARN] Failed to harvest {target['name']}: {e}")


if __name__ == "__main__":
    harvest_seeds()

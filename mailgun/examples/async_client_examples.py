"""Asynchronous examples for the Mailgun Python SDK."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from mailgun.client import AsyncClient

_HTML_CONTENT: str = """<body style="margin: 0; padding: 0;">
 <table border="1" cellpadding="0" cellspacing="0" width="100%">
  <tr>
   <td>
    Hello!
   </td>
  </tr>
 </table>
</body>"""


# ==============================================================================
# Domain Examples
# ==============================================================================


async def get_domains_async(api_key: str) -> None:
    """
    GET /domains
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domainlist.get()
        print("GET Domains:", response.json())


# ==============================================================================
# Messaging Examples
# ==============================================================================


async def post_message_async(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str
) -> None:
    """
    POST /<domain>/messages
    :return: None
    """
    data: dict[str, str] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello World",
        "html": _HTML_CONTENT,
        "o:tag": "Python test",
    }

    path1 = Path("mailgun/doc_tests/files/test1.txt")
    path2 = Path("mailgun/doc_tests/files/test2.txt")

    if not path1.exists() or not path2.exists():
        print(f"Files not found: {path1} or {path2}. Skipping message attachment upload.")
        return

    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    files: list[tuple[str, tuple[str, bytes]]] = [
        ("attachment", ("test1.txt", path1.read_bytes())),
        ("attachment", ("test2.txt", path2.read_bytes())),
    ]

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.messages.create(data=data, files=files, domain=domain)
        print("POST Message:", response.json())


# ==============================================================================
# Events Examples
# ==============================================================================


async def events_rejected_or_failed_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/events
    :return: None
    """
    params: dict[str, str] = {"event": "rejected OR failed"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.events.get(domain=domain, filters=params)
        print("GET Events (Rejected/Failed):", response.json())


# ==============================================================================
# Template Examples
# ==============================================================================


async def post_template_async(api_key: str, domain: str) -> None:
    """
    POST /<domain>/templates
    :return: None
    """
    data: dict[str, str] = {
        "name": "template.name1",
        "description": "template description",
        "template": "{{fname}} {{lname}}",
        "engine": "handlebars",
        "comment": "version comment",
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.templates.create(data=data, domain=domain)
        print("POST Template:", response.json())


# ==============================================================================
# Analytics Examples
# ==============================================================================


async def post_analytics_logs_async(api_key: str, domain: str) -> None:
    """
    # Metrics
    # POST /v1/analytics/logs
    :return: None
    """
    data: dict[str, Any] = {
        "start": "Wed, 24 Sep 2025 00:00:00 +0000",
        "end": "Thu, 25 Sep 2025 00:00:00 +0000",
        "filter": {
            "AND": [
                {
                    "attribute": "domain",
                    "comparator": "=",
                    "values": [{"label": domain, "value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "pagination": {
            "sort": "timestamp:asc",
            "limit": 50,
        },
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_logs.create(data=data)
        print("POST Analytics Logs:", response.json())


# ==============================================================================
# Execution
# ==============================================================================


async def main() -> None:
    """Main coroutine that orchestrates the execution of other coroutines."""
    api_key: str = os.environ.get("APIKEY", "")
    domain: str = os.environ.get("DOMAIN", "")

    # Fallbacks to prevent instant crashes if only partially configured
    msg_from: str = os.environ.get("MESSAGES_FROM", f"test_from@{domain}")
    msg_to: str = os.environ.get("MESSAGES_TO", f"test_to@{domain}")
    msg_cc: str = os.environ.get("MESSAGES_CC", f"test_cc@{domain}")

    if not api_key or not domain:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
        return

    print("=== Starting async operations ===\n")

    # Example 1: Running coroutines sequentially
    print("Example 1: Sequential execution")
    await get_domains_async(api_key=api_key)
    await events_rejected_or_failed_async(api_key=api_key, domain=domain)

    # Example 2: Running coroutines concurrently with gather
    print("\nExample 2: Concurrent execution with gather()")
    await asyncio.gather(
        post_message_async(
            api_key=api_key, domain=domain, from_email=msg_from, to_email=msg_to, cc_email=msg_cc
        ),
        post_template_async(api_key=api_key, domain=domain),
        post_analytics_logs_async(api_key=api_key, domain=domain),
    )

    print("\n=== All async operations completed ===")


if __name__ == "__main__":
    asyncio.run(main())

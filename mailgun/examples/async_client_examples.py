from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mailgun.client import AsyncClient


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
html: str = """<body style="margin: 0; padding: 0;">
 <table border="1" cellpadding="0" cellspacing="0" width="100%">
  <tr>
   <td>
    Hello!
   </td>
  </tr>
 </table>
</body>"""

client: AsyncClient = AsyncClient(auth=("api", key))


async def get_domains() -> None:
    """
    GET /domains
    :return:
    """
    data = await client.domainlist.get()
    print(data.json())


async def post_message() -> None:
    # Messages
    # POST /<domain>/messages
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello World",
        "html": html,
        "o:tag": "Python test",
    }
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    files = [
        (
            "attachment",
            ("test1.txt", Path("mailgun/doc_tests/files/test1.txt").read_bytes()),
        ),
        (
            "attachment",
            ("test2.txt", Path("mailgun/doc_tests/files/test2.txt").read_bytes()),
        ),
    ]

    async with AsyncClient(auth=("api", key)) as _client:
        req = await _client.messages.create(data=data, files=files, domain=domain)
    print(req.json())


async def events_rejected_or_failed() -> None:
    """
    GET /<domain>/events
    :return:
    """
    params = {"event": "rejected OR failed"}
    req = await client.events.get(domain=domain, filters=params)
    print(req.json())


# context manager approach examples:
async def post_template() -> None:
    """
    POST /<domain>/templates
    :return:
    """
    data = {
        "name": "template.name1",
        "description": "template description",
        "template": "{{fname}} {{lname}}",
        "engine": "handlebars",
        "comment": "version comment",
    }

    async with AsyncClient(auth=("api", key)) as _client:
        req = await _client.templates.create(data=data, domain=domain)
    print(req.json())


async def post_analytics_logs() -> None:
    """
    # Metrics
    # POST /v1/analytics/logs
    :return:
    """

    data = {
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

    async with AsyncClient(auth=("api", key)) as _client:
        req = await _client.analytics_logs.create(data=data)
    print(req.json())


async def main():
    """Main coroutine that orchestrates the execution of other coroutines."""
    print("=== Starting async operations ===\n")

    # # Example 1: Running coroutines sequentially
    print("Example 1: Sequential execution")
    await get_domains()
    await events_rejected_or_failed()

    # Example 2: Running coroutines concurrently with gather
    print("Example 2: Concurrent execution with gather()")
    await asyncio.gather(
        post_message(),
        post_template(),
        post_analytics_logs(),
    )

    print("\n=== All async operations completed ===")


if __name__ == "__main__":
    asyncio.run(main())

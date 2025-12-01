from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: AsyncClient = AsyncClient(auth=("api", key))


async def get_domains() -> None:
    """
    GET /domains
    :return:
    """
    data = await client.domainlist.get()
    print(data.json())


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

    # Example 1: Running coroutines sequentially
    print("Example 1: Sequential execution")
    await get_domains()
    await events_rejected_or_failed()

    # Example 2: Running coroutines concurrently with gather
    print("Example 2: Concurrent execution with gather()")
    await asyncio.gather(
        post_template(),
        post_analytics_logs(),
    )

    print("\n=== All async operations completed ===")


if __name__ == "__main__":
    asyncio.run(main())

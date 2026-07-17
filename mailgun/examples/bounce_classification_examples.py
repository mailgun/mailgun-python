"""Examples for Mailgun Bounce Classification API."""

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


def post_list_statistic_v2_sync(api_key: str, domain: str) -> None:
    """
    # Bounce Classification (Synchronous)
    # POST /v2/bounce-classification/metrics
    :return: None
    """
    payload: dict[str, Any] = {
        "start": "Wed, 12 Nov 2025 23:00:00 UTC",
        "end": "Thu, 13 Nov 2025 23:00:00 UTC",
        "resolution": "day",
        "duration": "24h0m0s",
        "dimensions": ["entity-name", "domain.name"],
        "metrics": [
            "critical_bounce_count",
            "non_critical_bounce_count",
            "critical_delay_count",
            "non_critical_delay_count",
            "delivered_smtp_count",
            "classified_failures_count",
            "critical_bounce_rate",
            "non_critical_bounce_rate",
            "critical_delay_rate",
            "non_critical_delay_rate",
        ],
        "filter": {
            "AND": [
                {
                    "attribute": "domain.name",
                    "comparator": "=",
                    "values": [{"value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "pagination": {"sort": "entity-name:asc", "limit": 10},
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}

    with Client(auth=("api", api_key)) as client:
        req = client.bounce_classification.create(data=payload, headers=headers)
        print(req.json())


async def post_list_statistic_v2_async(api_key: str, domain: str) -> None:
    """
    # Bounce Classification (Asynchronous)
    # POST /v2/bounce-classification/metrics
    :return: None
    """
    payload: dict[str, Any] = {
        "start": "Wed, 12 Nov 2025 23:00:00 UTC",
        "end": "Thu, 13 Nov 2025 23:00:00 UTC",
        "resolution": "day",
        "duration": "24h0m0s",
        "dimensions": ["entity-name", "domain.name"],
        "metrics": [
            "critical_bounce_count",
            "non_critical_bounce_count",
            "critical_delay_count",
            "non_critical_delay_count",
            "delivered_smtp_count",
            "classified_failures_count",
            "critical_bounce_rate",
            "non_critical_bounce_rate",
            "critical_delay_rate",
            "non_critical_delay_rate",
        ],
        "filter": {
            "AND": [
                {
                    "attribute": "domain.name",
                    "comparator": "=",
                    "values": [{"value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "pagination": {"sort": "entity-name:asc", "limit": 10},
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}

    async with AsyncClient(auth=("api", api_key)) as client:
        req = await client.bounce_classification.create(data=payload, headers=headers)
        print(req.json())


if __name__ == "__main__":
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables.")
    else:
        print("--- Running Synchronous Bounce Classification Example ---")
        post_list_statistic_v2_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Bounce Classification Example ---")
        asyncio.run(post_list_statistic_v2_async(api_key=API_KEY, domain=DOMAIN))

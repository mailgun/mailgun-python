"""Examples for fetching Mailgun Analytics Logs."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Analytics Logs Management (Synchronous)
# ==============================================================================


def post_analytics_logs_sync(api_key: str, domain: str) -> None:
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

    with Client(auth=("api", api_key)) as client:
        response = client.analytics_logs.create(data=data)
        print("POST Analytics Logs (Sync):", response.json())


# ==============================================================================
# Analytics Logs Management (Asynchronous)
# ==============================================================================


async def post_analytics_logs_async(api_key: str, domain: str) -> None:
    """
    # Metrics (Asynchronous)
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
        print("POST Analytics Logs (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        post_analytics_logs_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(post_analytics_logs_async(api_key=API_KEY, domain=DOMAIN))

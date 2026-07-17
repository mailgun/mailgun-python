"""Examples for fetching Mailgun Analytics Metrics."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Analytics Metrics Management (Synchronous)
# ==============================================================================


def post_analytics_metrics_sync(api_key: str, domain: str) -> None:
    """
    # Metrics
    # POST /v1/analytics/metrics
    :return: None
    """
    data: dict[str, Any] = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": ["accepted_count", "delivered_count", "clicked_rate", "opened_rate"],
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
        "include_aggregates": True,
    }

    with Client(auth=("api", api_key)) as client:
        response = client.analytics_metrics.create(data=data)
        print("POST Analytics Metrics (Sync):", response.json())


def post_analytics_usage_metrics_sync(api_key: str) -> None:
    """
    # Usage Metrics
    # POST /v1/analytics/usage/metrics
    :return: None
    """
    data: dict[str, Any] = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": [
            "accessibility_count",
            "accessibility_failed_count",
            "domain_blocklist_monitoring_count",
            "email_preview_count",
            "email_preview_failed_count",
            "email_validation_bulk_count",
            "email_validation_count",
            "email_validation_list_count",
            "email_validation_mailgun_count",
            "email_validation_mailjet_count",
            "email_validation_public_count",
            "email_validation_single_count",
            "email_validation_valid_count",
            "image_validation_count",
            "image_validation_failed_count",
            "ip_blocklist_monitoring_count",
            "link_validation_count",
            "link_validation_failed_count",
            "processed_count",
            "seed_test_count",
        ],
        "include_subaccounts": True,
        "include_aggregates": True,
    }

    with Client(auth=("api", api_key)) as client:
        response = client.analytics_usage_metrics.create(data=data)
        print("POST Analytics Usage Metrics (Sync):", response.json())


# ==============================================================================
# Analytics Metrics Management (Asynchronous)
# ==============================================================================


async def post_analytics_metrics_async(api_key: str, domain: str) -> None:
    """
    # Metrics (Asynchronous)
    # POST /v1/analytics/metrics
    :return: None
    """
    data: dict[str, Any] = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": ["accepted_count", "delivered_count", "clicked_rate", "opened_rate"],
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
        "include_aggregates": True,
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_metrics.create(data=data)
        print("POST Analytics Metrics (Async):", response.json())


async def post_analytics_usage_metrics_async(api_key: str) -> None:
    """
    # Usage Metrics (Asynchronous)
    # POST /v1/analytics/usage/metrics
    :return: None
    """
    data: dict[str, Any] = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": [
            "accessibility_count",
            "accessibility_failed_count",
            "domain_blocklist_monitoring_count",
            "email_preview_count",
            "email_preview_failed_count",
            "email_validation_bulk_count",
            "email_validation_count",
            "email_validation_list_count",
            "email_validation_mailgun_count",
            "email_validation_mailjet_count",
            "email_validation_public_count",
            "email_validation_single_count",
            "email_validation_valid_count",
            "image_validation_count",
            "image_validation_failed_count",
            "ip_blocklist_monitoring_count",
            "link_validation_count",
            "link_validation_failed_count",
            "processed_count",
            "seed_test_count",
        ],
        "include_subaccounts": True,
        "include_aggregates": True,
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_usage_metrics.create(data=data)
        print("POST Analytics Usage Metrics (Async):", response.json())


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
        post_analytics_metrics_sync(api_key=API_KEY, domain=DOMAIN)
        post_analytics_usage_metrics_sync(api_key=API_KEY)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(post_analytics_metrics_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(post_analytics_usage_metrics_async(api_key=API_KEY))

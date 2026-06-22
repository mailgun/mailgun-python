"""Examples for managing Mailgun Tags and fetching Tag Statistics."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Tag Management (Synchronous)
# ==============================================================================


def delete_tag_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    DELETE /<domain>/tags/<tag>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags.delete(domain=domain, tag_name=tag_name)
        print("DELETE Tag (Sync):", response.json())


def get_single_tag_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags.get(domain=domain, tag_name=tag_name)
        print("GET Single Tag (Sync):", response.json())


def get_tags_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/tags
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags.get(domain=domain)
        print("GET Tags (Sync):", response.json())


def put_single_tag_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    PUT /<domain>/tags/<tag>
    :return: None
    """
    data: dict[str, Any] = {"description": "Python testtt"}
    with Client(auth=("api", api_key)) as client:
        response = client.tags.put(domain=domain, tag_name=tag_name, data=data)
        print("PUT Single Tag (Sync):", response.json())


# ==============================================================================
# Tag Statistics & Aggregates (Synchronous)
# ==============================================================================


def get_aggregate_countries_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/countries
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags_stats_aggregates_countries.get(domain=domain, tag_name=tag_name)
        print("GET Aggregate Countries (Sync):", response.json())


def get_aggregate_devices_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/devices
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags_stats_aggregates_devices.get(domain=domain, tag_name=tag_name)
        print("GET Aggregate Devices (Sync):", response.json())


def get_aggregate_providers_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/providers
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.tags_stats_aggregates_providers.get(domain=domain, tag_name=tag_name)
        print("GET Aggregate Providers (Sync):", response.json())


def get_tag_stats_sync(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats
    :return: None
    """
    filters: dict[str, str] = {"event": "accepted"}
    with Client(auth=("api", api_key)) as client:
        response = client.tags_stats.get(domain=domain, filters=filters, tag_name=tag_name)
        print("GET Tag Stats (Sync):", response.json())


# ==============================================================================
# Tag Management (Asynchronous)
# ==============================================================================


async def delete_tag_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    DELETE /<domain>/tags/<tag> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags.delete(domain=domain, tag_name=tag_name)
        print("DELETE Tag (Async):", response.json())


async def get_single_tag_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags.get(domain=domain, tag_name=tag_name)
        print("GET Single Tag (Async):", response.json())


async def get_tags_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/tags (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags.get(domain=domain)
        print("GET Tags (Async):", response.json())


async def put_single_tag_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    PUT /<domain>/tags/<tag> (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"description": "Python testtt"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags.put(domain=domain, tag_name=tag_name, data=data)
        print("PUT Single Tag (Async):", response.json())


# ==============================================================================
# Tag Statistics & Aggregates (Asynchronous)
# ==============================================================================


async def get_aggregate_countries_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/countries (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags_stats_aggregates_countries.get(
            domain=domain, tag_name=tag_name
        )
        print("GET Aggregate Countries (Async):", response.json())


async def get_aggregate_devices_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/devices (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags_stats_aggregates_devices.get(domain=domain, tag_name=tag_name)
        print("GET Aggregate Devices (Async):", response.json())


async def get_aggregate_providers_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/providers (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags_stats_aggregates_providers.get(
            domain=domain, tag_name=tag_name
        )
        print("GET Aggregate Providers (Async):", response.json())


async def get_tag_stats_async(api_key: str, domain: str, tag_name: str) -> None:
    """
    GET /<domain>/tags/<tag>/stats (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"event": "accepted"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.tags_stats.get(domain=domain, filters=filters, tag_name=tag_name)
        print("GET Tag Stats (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    TEST_TAG: str = "Python test"
    TAG: str = "September newsletter"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_aggregate_devices_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TAG)

        # Additional Sync tests to execute:
        # get_tags_sync(api_key=API_KEY, domain=DOMAIN)
        # put_single_tag_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TEST_TAG)
        # get_single_tag_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TEST_TAG)
        # get_tag_stats_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TEST_TAG)
        # get_aggregate_countries_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TAG)
        # get_aggregate_providers_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TAG)
        # delete_tag_sync(api_key=API_KEY, domain=DOMAIN, tag_name=TEST_TAG)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(get_aggregate_devices_async(api_key=API_KEY, domain=DOMAIN, tag_name=TAG))
        # asyncio.run(get_tags_async(api_key=API_KEY, domain=DOMAIN))

"""Examples for managing Mailgun IP Pools and Domain Linkage."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# IP Pool Management (Synchronous)
# ==============================================================================


def get_ippools_sync(api_key: str, domain: str) -> None:
    """
    GET /v1/ip_pools
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.ippools.get(domain=domain)
        print("GET IP Pools (Sync):", response.json())


def create_ippool_sync(api_key: str, domain: str) -> None:
    """
    POST /v1/ip_pools
    :return: None
    """
    post_data: dict[str, Any] = {
        "name": "test_pool1",
        "description": "Test",
        "ips": ["1.2.3.4"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.ippools.create(domain=domain, data=post_data)
        print("POST Create IP Pool (Sync):", response.json())


def update_ippool_sync(api_key: str, domain: str, pool_id: str) -> None:
    """
    PATCH /v1/ip_pools/{pool_id}
    :return: None
    """
    data: dict[str, str] = {
        "name": "test_pool3",
        "description": "Test3",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.ippools.patch(domain=domain, data=data, pool_id=pool_id)
        print("PATCH Update IP Pool (Sync):", response.json())


def delete_ippool_sync(api_key: str, domain: str, pool_id: str) -> None:
    """
    DELETE /v1/ip_pools/{pool_id}
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.ippools.delete(domain=domain, pool_id=pool_id)
        print("DELETE IP Pool (Sync):", response.json())


# ==============================================================================
# Domain IP Pool Linkage (Synchronous)
# ==============================================================================


def link_ippool_sync(api_key: str, domain: str, pool_id: str) -> None:
    """
    POST /v3/domains/{domain_name}/ips
    :return: None
    """
    data: dict[str, str] = {"pool_id": pool_id}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_ips.create(domain=domain, data=data)
        print("POST Link IP Pool (Sync):", response.json())


def unlink_ippool_sync(api_key: str, domain: str, pool_id: str) -> None:
    """
    DELETE /v3/domains/{domain_name}/ips/ip_pool
    :return: None
    """
    filters: dict[str, str] = {"pool_id": pool_id}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_ips.delete(domain=domain, filters=filters, unlink_pool=True)
        print("DELETE Unlink IP Pool (Sync):", response.json())


# ==============================================================================
# IP Pool Management (Asynchronous)
# ==============================================================================


async def get_ippools_async(api_key: str, domain: str) -> None:
    """
    GET /v1/ip_pools (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ippools.get(domain=domain)
        print("GET IP Pools (Async):", response.json())


async def create_ippool_async(api_key: str, domain: str) -> None:
    """
    POST /v1/ip_pools (Asynchronous)
    :return: None
    """
    post_data: dict[str, Any] = {
        "name": "test_pool1_async",
        "description": "Test Async",
        "ips": ["1.2.3.4"],
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ippools.create(domain=domain, data=post_data)
        print("POST Create IP Pool (Async):", response.json())


async def update_ippool_async(api_key: str, domain: str, pool_id: str) -> None:
    """
    PATCH /v1/ip_pools/{pool_id} (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {
        "name": "test_pool3_async",
        "description": "Test3 Async",
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ippools.patch(domain=domain, data=data, pool_id=pool_id)
        print("PATCH Update IP Pool (Async):", response.json())


async def delete_ippool_async(api_key: str, domain: str, pool_id: str) -> None:
    """
    DELETE /v1/ip_pools/{pool_id} (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ippools.delete(domain=domain, pool_id=pool_id)
        print("DELETE IP Pool (Async):", response.json())


# ==============================================================================
# Domain IP Pool Linkage (Asynchronous)
# ==============================================================================


async def link_ippool_async(api_key: str, domain: str, pool_id: str) -> None:
    """
    POST /v3/domains/{domain_name}/ips (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {"pool_id": pool_id}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_ips.create(domain=domain, data=data)
        print("POST Link IP Pool (Async):", response.json())


async def unlink_ippool_async(api_key: str, domain: str, pool_id: str) -> None:
    """
    DELETE /v3/domains/{domain_name}/ips/ip_pool (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"pool_id": pool_id}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_ips.delete(domain=domain, filters=filters, unlink_pool=True)
        print("DELETE Unlink IP Pool (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    # Dummy identifiers for example purposes
    POOL_ID: str = "123456789"
    LINK_POOL_ID: str = "987654321"
    UNLINK_POOL_ID: str = "000111222333444555"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_ippools_sync(api_key=API_KEY, domain=DOMAIN)
        # create_ippool_sync(api_key=API_KEY, domain=DOMAIN)
        # update_ippool_sync(api_key=API_KEY, domain=DOMAIN, pool_id=POOL_ID)
        # delete_ippool_sync(api_key=API_KEY, domain=DOMAIN, pool_id=POOL_ID)

        # link_ippool_sync(api_key=API_KEY, domain=DOMAIN, pool_id=LINK_POOL_ID)
        # unlink_ippool_sync(api_key=API_KEY, domain=DOMAIN, pool_id=UNLINK_POOL_ID)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(get_ippools_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(create_ippool_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(update_ippool_async(api_key=API_KEY, domain=DOMAIN, pool_id=POOL_ID))
        # asyncio.run(delete_ippool_async(api_key=API_KEY, domain=DOMAIN, pool_id=POOL_ID))

        # asyncio.run(link_ippool_async(api_key=API_KEY, domain=DOMAIN, pool_id=LINK_POOL_ID))
        # asyncio.run(unlink_ippool_async(api_key=API_KEY, domain=DOMAIN, pool_id=UNLINK_POOL_ID))

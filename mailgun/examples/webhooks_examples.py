"""Examples for managing Mailgun Domain Webhooks."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client

# ==============================================================================
# Webhooks Management (Synchronous)
# ==============================================================================


def create_webhook_sync(api_key: str, domain: str) -> None:
    """
    POST /v3/domains/<domain>/webhooks
    :return: None
    """
    data: dict[str, Any] = {"id": "clicked", "url": ["https://facebook.com"]}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_webhooks.create(domain=domain, data=data)
        print("POST Webhook (Sync):", response.json())


def delete_webhook_sync(api_key: str, domain: str) -> None:
    """
    DELETE /v3/domains/<domain>/webhooks/<webhook_name>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        # Use webhook_name kwarg for safe path interpolation
        response = client.domains_webhooks.delete(domain=domain, webhook_name="clicked")
        print("DELETE Webhook (Sync):", response.json())


def get_webhook_sync(api_key: str, domain: str) -> None:
    """
    GET /v3/domains/<domain>/webhooks/<webhook_name>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_webhooks.get(domain=domain, webhook_name="clicked")
        print("GET Single Webhook (Sync):", response.json())


def get_webhooks_sync(api_key: str, domain: str) -> None:
    """
    GET /v3/domains/<domain>/webhooks
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_webhooks.get(domain=domain)
        print("GET Webhooks (Sync):", response.json())


def put_webhook_sync(api_key: str, domain: str) -> None:
    """
    PUT /v3/domains/<domain>/webhooks/<webhook_name>
    :return: None
    """
    data: dict[str, Any] = {
        "url": ["https://facebook.com", "https://google.com"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.domains_webhooks.put(domain=domain, webhook_name="clicked", data=data)
        print("PUT Webhook (Sync):", response.json())


# ==============================================================================
# Webhooks Management (Asynchronous)
# ==============================================================================


async def create_webhook_async(api_key: str, domain: str) -> None:
    """
    POST /v3/domains/<domain>/webhooks (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"id": "clicked", "url": ["https://facebook.com"]}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_webhooks.create(domain=domain, data=data)
        print("POST Webhook (Async):", response.json())


async def delete_webhook_async(api_key: str, domain: str) -> None:
    """
    DELETE /v3/domains/<domain>/webhooks/<webhook_name> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_webhooks.delete(domain=domain, webhook_name="clicked")
        print("DELETE Webhook (Async):", response.json())


async def get_webhook_async(api_key: str, domain: str) -> None:
    """
    GET /v3/domains/<domain>/webhooks/<webhook_name> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_webhooks.get(domain=domain, webhook_name="clicked")
        print("GET Single Webhook (Async):", response.json())


async def get_webhooks_async(api_key: str, domain: str) -> None:
    """
    GET /v3/domains/<domain>/webhooks (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_webhooks.get(domain=domain)
        print("GET Webhooks (Async):", response.json())


async def put_webhook_async(api_key: str, domain: str) -> None:
    """
    PUT /v3/domains/<domain>/webhooks/<webhook_name> (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "url": ["https://facebook.com", "https://google.com"],
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_webhooks.put(
            domain=domain, webhook_name="clicked", data=data
        )
        print("PUT Webhook (Async):", response.json())


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
        create_webhook_sync(api_key=API_KEY, domain=DOMAIN)
        get_webhooks_sync(api_key=API_KEY, domain=DOMAIN)

        # Additional Sync operations available for testing:
        # get_webhook_sync(api_key=API_KEY, domain=DOMAIN)
        # put_webhook_sync(api_key=API_KEY, domain=DOMAIN)
        # delete_webhook_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(create_webhook_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(get_webhooks_async(api_key=API_KEY, domain=DOMAIN))

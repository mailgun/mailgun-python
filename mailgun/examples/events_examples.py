"""Examples for querying and retrieving Mailgun routing events and stored messages."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Synchronous Examples
# ==============================================================================


def get_domain_events_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/events
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.events.get(domain=domain)
        print("GET Domain Events (Sync):", response.json())


def events_by_recipient_sync(api_key: str, domain: str, recipient: str) -> None:
    """
    GET /<domain>/events
    :return: None
    """
    params: dict[str, Any] = {
        "begin": "Tue, 24 Nov 2020 09:00:00 -0000",
        "ascending": "yes",
        "limit": 10,
        "pretty": "yes",
        "recipient": recipient,
    }
    with Client(auth=("api", api_key)) as client:
        response = client.events.get(domain=domain, filters=params)
        print("Events by Recipient (Sync):", response.json())


def events_rejected_or_failed_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/events
    :return: None
    """
    params: dict[str, str] = {"event": "rejected OR failed"}
    with Client(auth=("api", api_key)) as client:
        response = client.events.get(domain=domain, filters=params)
        print("Rejected or Failed Events (Sync):", response.json())


def view_message_with_storage_url_sync(api_key: str, domain: str) -> None:
    """
    /v3/domains/<domain>/messages/{storage_url}
    :return: None
    """
    params: dict[str, int] = {"limit": 1}

    with Client(auth=("api", api_key)) as client:
        events_response = client.events.get(domain=domain, filters=params)
        items = events_response.json().get("items", [])

        if items and "storage" in items[0]:
            storage_info = items[0].get("storage", {})
            storage_url = storage_info.get("url")

            if storage_url:
                # Proceed with storage_url
                print(f"Found storage URL: {storage_url}")
            else:
                # Handle the case where no URL is found
                print("No storage URL available for this event.")
            # Retrieve the full message using the exact storage URL
            message_response = client.domains_messages.get(
                domain=domain, api_storage_url=storage_url
            )
            print("View Stored Message (Sync):", message_response.json())
        else:
            print("No stored messages found in recent events.")


# ==============================================================================
# Asynchronous Examples
# ==============================================================================


async def get_domain_events_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/events (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.events.get(domain=domain)
        print("GET Domain Events (Async):", response.json())


async def events_by_recipient_async(api_key: str, domain: str, recipient: str) -> None:
    """
    GET /<domain>/events (Asynchronous)
    :return: None
    """
    params: dict[str, Any] = {
        "begin": "Tue, 24 Nov 2020 09:00:00 -0000",
        "ascending": "yes",
        "limit": 10,
        "pretty": "yes",
        "recipient": recipient,
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.events.get(domain=domain, filters=params)
        print("Events by Recipient (Async):", response.json())


async def events_rejected_or_failed_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/events (Asynchronous)
    :return: None
    """
    params: dict[str, str] = {"event": "rejected OR failed"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.events.get(domain=domain, filters=params)
        print("Rejected or Failed Events (Async):", response.json())


async def view_message_with_storage_url_async(api_key: str, domain: str) -> None:
    """
    /v3/domains/<domain>/messages/{storage_url} (Asynchronous)
    :return: None
    """
    params: dict[str, int] = {"limit": 1}

    async with AsyncClient(auth=("api", api_key)) as client:
        events_response = await client.events.get(domain=domain, filters=params)
        items = events_response.json().get("items", [])

        # Check if storage exists AND contains the 'url' key
        if items and "storage" in items[0] and "url" in items[0]["storage"]:
            storage_url: str = items[0]["storage"]["url"]

            # Retrieve the full message asynchronously
            message_response = await client.domains_messages.get(
                domain=domain, api_storage_url=storage_url
            )
            print("View Stored Message (Async):", message_response.json())
        else:
            print("No stored messages found in recent events.")


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")
    RECIPIENT: str = os.environ.get("VALIDATION_ADDRESS_1", f"test@{DOMAIN}")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_domain_events_sync(api_key=API_KEY, domain=DOMAIN)
        events_by_recipient_sync(api_key=API_KEY, domain=DOMAIN, recipient=RECIPIENT)
        events_rejected_or_failed_sync(api_key=API_KEY, domain=DOMAIN)
        view_message_with_storage_url_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(get_domain_events_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(events_by_recipient_async(api_key=API_KEY, domain=DOMAIN, recipient=RECIPIENT))
        asyncio.run(events_rejected_or_failed_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(view_message_with_storage_url_async(api_key=API_KEY, domain=DOMAIN))

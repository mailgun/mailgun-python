"""Examples for using Mailgun TypedDict schemas for static payload validation."""

from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient, Client
from mailgun.types import SendMessagePayload


# ==============================================================================
# TypedDict Usage (Synchronous)
# ==============================================================================


def send_message_sync(api_key: str, domain: str, to_email: str) -> None:
    """
    Send an email using the SendMessagePayload TypedDict for strict validation.
    :return: None
    """
    # The IDE will seamlessly auto-complete "from", "to", "subject", "text", etc.
    my_data: SendMessagePayload = {
        "from": f"admin@{domain}",
        "to": [to_email],
        "subject": "System Update (Sync)",
        "text": "Downtime at midnight.",
    }

    with Client(auth=("api", api_key), api_url="https://api.mailgun.net/v3") as client:
        response = client.messages.create(domain=domain, data=my_data)
        print(f"Sync Response: {response.status_code} - {response.text.strip()}")


# ==============================================================================
# TypedDict Usage (Asynchronous)
# ==============================================================================


async def send_message_async(api_key: str, domain: str, to_email: str) -> None:
    """
    Send an email asynchronously using the SendMessagePayload TypedDict.
    :return: None
    """
    my_data: SendMessagePayload = {
        "from": f"admin@{domain}",
        "to": [to_email],
        "subject": "System Update (Async)",
        "text": "Downtime at midnight.",
    }

    async with AsyncClient(auth=("api", api_key), api_url="https://api.mailgun.net/v3") as client:
        response = await client.messages.create(domain=domain, data=my_data)
        print(f"Async Response: {response.status_code} - {response.text.strip()}")


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime, falling back to common keys
    API_KEY: str = os.environ.get("MAILGUN_API_KEY", os.environ.get("APIKEY", ""))
    DOMAIN: str = os.environ.get("MAILGUN_DOMAIN", os.environ.get("DOMAIN", ""))
    TO_EMAIL: str = os.environ.get("MESSAGES_TO", "customer@example.com")

    if not API_KEY or not DOMAIN:
        print("Please set the 'MAILGUN_API_KEY' and 'MAILGUN_DOMAIN' environment variables.")
    else:
        print("--- Running Synchronous Examples ---")
        print(f"Sending test email via TypedDict schema to {DOMAIN}...")
        send_message_sync(api_key=API_KEY, domain=DOMAIN, to_email=TO_EMAIL)

        print("\n--- Running Asynchronous Examples ---")
        print(f"Sending async test email via TypedDict schema to {DOMAIN}...")
        asyncio.run(send_message_async(api_key=API_KEY, domain=DOMAIN, to_email=TO_EMAIL))

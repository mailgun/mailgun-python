"""Examples for managing Mailgun API Keys."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# API Key Management (Synchronous)
# ==============================================================================


def delete_key_sync(api_key: str, mailgun_email: str) -> None:
    """
    DELETE /v1/keys/{key_id}
    :return: None
    """
    filters: dict[str, str] = {"domain_name": "python.test.domain5", "kind": "web"}
    with Client(auth=("api", api_key)) as client:
        response1 = client.keys.get(filters=filters)
        items: list[dict[str, Any]] = response1.json().get("items", [])

        for item in items:
            if mailgun_email == item.get("requestor"):  # codespell:disable-line
                response2 = client.keys.delete(key_id=item["id"])
                print("DELETE Key (Sync):", response2.json())


def get_keys_sync(api_key: str) -> None:
    """
    GET /v1/keys
    :return: None
    """
    filters: dict[str, str] = {"domain_name": "python.test.domain5", "kind": "web"}
    with Client(auth=("api", api_key)) as client:
        response = client.keys.get(filters=filters)
        print("GET Keys (Sync):", response.json())


def post_keys_sync(
    api_key: str, mailgun_email: str, role: str, user_id: str, user_name: str
) -> None:
    """
    POST /v1/keys

    This code generates a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID values.
    This is returned by the API in the "secret":"API_KEY" key/value pair. This key will authenticate the call (Get one's own user details) made to the /v5/users/me endpoint,   # pragma: allowlist secret
    and will return the user's data associated with the USER_EMAIL and USER_ID values.

    Important Notes:
    USER_EMAIL - The user login email address of the user that is trying to make the call to the /v5/users/me endpoint.
    SECONDS - How many seconds you want the key to be active before it expires.
    ROLE - The role of the API Key. This dictates what permissions the key has (https://help.mailgun.com/hc/en-us/articles/26016288026907-API-Key-Roles)
    USER_ID - The internal User ID of the user that is trying to call the /v5/users/me endpoint. This is present in the URL in the address bar when viewing the User details in the GUI or in Admin. Both will show /users/USER_ID in the address.
    DESCRIPTION - Description of the key.

    :return: None
    """
    data: dict[str, str] = {
        "email": mailgun_email,
        "domain_name": "python.test.domain5",
        "kind": "web",
        "expiration": "3600",
        "role": role,
        "user_id": user_id,
        "user_name": user_name,
        "description": "a new key",
    }

    headers: dict[str, str] = {"Content-Type": "multipart/form-data"}

    with Client(auth=("api", api_key)) as client:
        response = client.keys.create(data=data, headers=headers)
        print("POST Keys (Sync):", response.json())


def regenerate_key_sync(api_key: str) -> None:
    """
    POST /v1/keys/public
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.keys_public.create()
        print("Regenerate Key (Sync):", response.json())


# ==============================================================================
# API Key Management (Asynchronous)
# ==============================================================================


async def delete_key_async(api_key: str, mailgun_email: str) -> None:
    """
    DELETE /v1/keys/{key_id} (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"domain_name": "python.test.domain5", "kind": "web"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response1 = await client.keys.get(filters=filters)
        items: list[dict[str, Any]] = response1.json().get("items", [])

        for item in items:
            if mailgun_email == item.get("requestor"):  # codespell:disable-line
                response2 = await client.keys.delete(key_id=item["id"])
                print("DELETE Key (Async):", response2.json())


async def get_keys_async(api_key: str) -> None:
    """
    GET /v1/keys (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"domain_name": "python.test.domain5", "kind": "web"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.keys.get(filters=filters)
        print("GET Keys (Async):", response.json())


async def post_keys_async(
    api_key: str, mailgun_email: str, role: str, user_id: str, user_name: str
) -> None:
    """
    POST /v1/keys (Asynchronous)

    This code generates a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID values.
    This is returned by the API in the "secret":"API_KEY" key/value pair. This key will authenticate the call (Get one's own user details) made to the /v5/users/me endpoint,   # pragma: allowlist secret
    and will return the user's data associated with the USER_EMAIL and USER_ID values.

    Important Notes:
    USER_EMAIL - The user login email address of the user that is trying to make the call to the /v5/users/me endpoint.
    SECONDS - How many seconds you want the key to be active before it expires.
    ROLE - The role of the API Key. This dictates what permissions the key has (https://help.mailgun.com/hc/en-us/articles/26016288026907-API-Key-Roles)
    USER_ID - The internal User ID of the user that is trying to call the /v5/users/me endpoint. This is present in the URL in the address bar when viewing the User details in the GUI or in Admin. Both will show /users/USER_ID in the address.
    DESCRIPTION - Description of the key.

    :return: None
    """
    data: dict[str, str] = {
        "email": mailgun_email,
        "domain_name": "python.test.domain5",
        "kind": "web",
        "expiration": "3600",
        "role": role,
        "user_id": user_id,
        "user_name": user_name,
        "description": "a new key",
    }

    headers: dict[str, str] = {"Content-Type": "multipart/form-data"}

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.keys.create(data=data, headers=headers)
        print("POST Keys (Async):", response.json())


async def regenerate_key_async(api_key: str) -> None:
    """
    POST /v1/keys/public (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.keys_public.create()
        print("Regenerate Key (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    MAILGUN_EMAIL: str = os.environ.get("MAILGUN_EMAIL", "test@example.com")
    ROLE: str = os.environ.get("ROLE", "admin")
    USER_ID: str = os.environ.get("USER_ID", "12345")
    USER_NAME: str = os.environ.get("USER_NAME", "Test User")

    if not API_KEY or not MAILGUN_EMAIL or not ROLE or not USER_ID or not USER_NAME:
        print(
            "Please set the 'APIKEY', 'MAILGUN_EMAIL', 'ROLE', 'USER_ID', and "
            "'USER_NAME' environment variables to run examples."
        )
    else:
        print("--- Running Synchronous Examples ---")
        # get_keys_sync(api_key=API_KEY)
        post_keys_sync(
            api_key=API_KEY,
            mailgun_email=MAILGUN_EMAIL,
            role=ROLE,
            user_id=USER_ID,
            user_name=USER_NAME,
        )
        get_keys_sync(api_key=API_KEY)
        delete_key_sync(api_key=API_KEY, mailgun_email=MAILGUN_EMAIL)
        get_keys_sync(api_key=API_KEY)
        regenerate_key_sync(api_key=API_KEY)
        get_keys_sync(api_key=API_KEY)

        print("\n--- Running Asynchronous Examples ---")
        # asyncio.run(get_keys_async(api_key=API_KEY))
        asyncio.run(
            post_keys_async(
                api_key=API_KEY,
                mailgun_email=MAILGUN_EMAIL,
                role=ROLE,
                user_id=USER_ID,
                user_name=USER_NAME,
            )
        )
        asyncio.run(get_keys_async(api_key=API_KEY))
        asyncio.run(delete_key_async(api_key=API_KEY, mailgun_email=MAILGUN_EMAIL))
        asyncio.run(get_keys_async(api_key=API_KEY))
        asyncio.run(regenerate_key_async(api_key=API_KEY))
        asyncio.run(get_keys_async(api_key=API_KEY))

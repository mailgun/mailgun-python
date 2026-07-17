"""Examples for managing Mailgun Users and Account Details."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# User Management (Synchronous)
# ==============================================================================


def get_own_user_details_sync(
    api_key: str, mailgun_email: str, role: str, user_id: str, user_name: str
) -> None:
    """
    GET /v5/users/me

    Please note, for the command("Get one's own user details") to be successful, you must use a Web type API key for the call. Private type API keys will Not work.
    The below Call will generate a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID  values.
    This is returned by the API in the "secret":"API_KEY" key/value pair.  # pragma: allowlist secret
    This key will authenticate the call(Get one's own user details) made to the /v5/users/me endpoint, and will return the user's data associated with the USER_EMAIL and USER_ID values.

    see https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/keys/api.(*keysapi).createkey-fm-7

    Important Notes:
    API_KEY - Private API Key
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

    secret: str | None = None

    # Step 1: Create the Web API Key
    with Client(auth=("api", api_key)) as client:
        response1 = client.keys.create(data=data, headers=headers)
        print("POST Create Key (Sync):", response1.json())

        # Safely extract the secret
        key_data = response1.json().get("key", {})
        secret = key_data.get("secret")

    if not secret:
        print("Failed to retrieve secret key. Aborting user lookup.")
        return

    # Step 2: Use the new Web API Key to get own user details
    with Client(auth=("api", secret)) as client_with_secret_key:
        response2 = client_with_secret_key.users.get(user_id="me")
        print("GET Own User Details (Sync):", response2.json())


def get_user_details_sync(api_key: str, mailgun_email: str, role: str) -> None:
    """
    GET /v5/users/{user_id}
    :return: None
    """
    filters: dict[str, str] = {"role": role, "limit": "0", "skip": "0"}

    with Client(auth=("api", api_key)) as client:
        response1 = client.users.get(filters=filters)
        users: list[dict[str, Any]] = response1.json().get("users", [])

        for user in users:
            if mailgun_email == user.get("email"):
                response2 = client.users.get(user_id=user["id"])
                print("GET Specific User Details (Sync):", response2.json())


def get_users_sync(api_key: str, role: str) -> None:
    """
    GET /v5/users
    :return: None
    """
    filters: dict[str, str] = {"role": role, "limit": "0", "skip": "0"}
    with Client(auth=("api", api_key)) as client:
        response = client.users.get(filters=filters)
        print("GET Users (Sync):", response.json())


# ==============================================================================
# User Management (Asynchronous)
# ==============================================================================


async def get_own_user_details_async(
    api_key: str, mailgun_email: str, role: str, user_id: str, user_name: str
) -> None:
    """
    GET /v5/users/me (Asynchronous)
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

    secret: str | None = None

    # Step 1: Create the Web API Key
    async with AsyncClient(auth=("api", api_key)) as client:
        response1 = await client.keys.create(data=data, headers=headers)
        print("POST Create Key (Async):", response1.json())

        # Safely extract the secret
        key_data = response1.json().get("key", {})
        secret = key_data.get("secret")

    if not secret:
        print("Failed to retrieve secret key. Aborting async user lookup.")
        return

    # Step 2: Use the new Web API Key to get own user details
    async with AsyncClient(auth=("api", secret)) as client_with_secret_key:
        response2 = await client_with_secret_key.users.get(user_id="me")
        print("GET Own User Details (Async):", response2.json())


async def get_user_details_async(api_key: str, mailgun_email: str, role: str) -> None:
    """
    GET /v5/users/{user_id} (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"role": role, "limit": "0", "skip": "0"}

    async with AsyncClient(auth=("api", api_key)) as client:
        response1 = await client.users.get(filters=filters)
        users: list[dict[str, Any]] = response1.json().get("users", [])

        for user in users:
            if mailgun_email == user.get("email"):
                response2 = await client.users.get(user_id=user["id"])
                print("GET Specific User Details (Async):", response2.json())


async def get_users_async(api_key: str, role: str) -> None:
    """
    GET /v5/users (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"role": role, "limit": "0", "skip": "0"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.users.get(filters=filters)
        print("GET Users (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    MAILGUN_EMAIL: str = os.environ.get("MAILGUN_EMAIL", "test@mailgun.com")
    ROLE: str = os.environ.get("ROLE", "admin")
    USER_ID: str = os.environ.get("USER_ID", "12345")
    USER_NAME: str = os.environ.get("USER_NAME", "Test User")

    if not API_KEY:
        print("Please set the 'APIKEY' environment variable to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_users_sync(api_key=API_KEY, role=ROLE)
        # get_own_user_details_sync(
        #     api_key=API_KEY,
        #     mailgun_email=MAILGUN_EMAIL,
        #     role=ROLE,
        #     user_id=USER_ID,
        #     user_name=USER_NAME
        # )
        # get_user_details_sync(api_key=API_KEY, mailgun_email=MAILGUN_EMAIL, role=ROLE)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(get_users_async(api_key=API_KEY, role=ROLE))
        # asyncio.run(
        #     get_own_user_details_async(
        #         api_key=API_KEY,
        #         mailgun_email=MAILGUN_EMAIL,
        #         role=ROLE,
        #         user_id=USER_ID,
        #         user_name=USER_NAME
        #     )
        # )
        # asyncio.run(get_user_details_async(api_key=API_KEY, mailgun_email=MAILGUN_EMAIL, role=ROLE))

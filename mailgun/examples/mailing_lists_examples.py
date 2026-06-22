"""Examples for managing Mailgun Mailing Lists and their Members."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Mailing Lists Management (Synchronous)
# ==============================================================================


def delete_list_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    DELETE /lists/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists.delete(domain=domain, address=list_address)
        print("DELETE List (Sync):", response.json())


def get_list_pages_sync(api_key: str, domain: str) -> None:
    """
    GET /lists/pages
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists_pages.get(domain=domain)
        print("GET List Pages (Sync):", response.json())


def get_list_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists.get(domain=domain, address=list_address)
        print("GET List (Sync):", response.json())


def post_list_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists
    :return: None
    """
    data: dict[str, str] = {
        "address": list_address,
        "description": "Mailgun developers list",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.lists.create(domain=domain, data=data)
        print("POST List (Sync):", response.json())


def put_list_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    PUT /lists/<address>
    :return: None
    """
    data: dict[str, str] = {"description": "Mailgun developers list 121212"}
    with Client(auth=("api", api_key)) as client:
        response = client.lists.put(domain=domain, data=data, address=list_address)
        print("PUT List (Sync):", response.json())


# ==============================================================================
# Mailing List Validation (Synchronous)
# ==============================================================================
# Note: Email Validations are only available for paid accounts.


def delete_list_validation_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    DELETE /lists/<address>/validate
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists.delete(domain=domain, address=list_address, validate=True)
        print("DELETE List Validation (Sync):", response.json())


def get_list_validation_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/validate
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists.get(domain=domain, address=list_address, validate=True)
        print("GET List Validation (Sync):", response.json())


def post_list_validation_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists/<address>/validate
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists.create(domain=domain, address=list_address, validate=True)
        print("POST List Validation (Sync):", response.json())


# ==============================================================================
# Mailing List Members Management (Synchronous)
# ==============================================================================


def delete_list_member_sync(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    DELETE /lists/<address>/members/<member_address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.delete(
            domain=domain,
            address=list_address,
            member_address=member_address,
        )
        print("DELETE List Member (Sync):", response.json())


def get_list_member_sync(api_key: str, domain: str, list_address: str, member_address: str) -> None:
    """
    GET /lists/<address>/members/<member_address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.get(
            domain=domain,
            address=list_address,
            member_address=member_address,
        )
        print("GET List Member (Sync):", response.json())


def get_list_members_pages_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/members/pages
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members_pages.get(domain=domain, address=list_address)
        print("GET List Members Pages (Sync):", response.json())


def get_list_members_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/members
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.get(domain=domain, address=list_address)
        print("GET List Members (Sync):", response.json())


def post_list_member_sync(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    POST /lists/<address>/members
    :return: None
    """
    data: dict[str, Any] = {
        "subscribed": True,
        "address": member_address,
        "name": "Bob Bar",
        "description": "Developer",
        "vars": '{"age": 26}',
    }
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.create(domain=domain, address=list_address, data=data)
        print("POST List Member (Sync):", response.json())


def post_list_members_json_sync(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists/<address>/members.json
    :return: None
    """
    data: dict[str, Any] = {
        "upsert": True,
        "members": '[{"address": "Alice <alice@example.com>", "vars": {"age": 26}},'
        '{"name": "Bob1", "address": "bob2@example.com", "vars": {"age": 34}}]',
    }
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.create(
            domain=domain,
            address=list_address,
            data=data,
            multiple=True,
        )
        print("POST List Members JSON (Sync):", response.json())


def put_list_member_sync(api_key: str, domain: str, list_address: str, member_address: str) -> None:
    """
    PUT /lists/<address>/members/<member_address>
    :return: None
    """
    data: dict[str, Any] = {
        "subscribed": True,
        "address": member_address,
        "name": "Bob Bar 2",
        "description": "Developer",
        "vars": '{"age": 28}',
    }
    with Client(auth=("api", api_key)) as client:
        response = client.lists_members.put(
            domain=domain,
            address=list_address,
            data=data,
            member_address=member_address,
        )
        print("PUT List Member (Sync):", response.json())


# ==============================================================================
# Mailing Lists Management (Asynchronous)
# ==============================================================================


async def delete_list_async(api_key: str, domain: str, list_address: str) -> None:
    """
    DELETE /lists/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.delete(domain=domain, address=list_address)
        print("DELETE List (Async):", response.json())


async def get_list_async(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.get(domain=domain, address=list_address)
        print("GET List (Async):", response.json())


async def get_list_pages_async(api_key: str, domain: str) -> None:
    """
    GET /lists/pages (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_pages.get(domain=domain)
        print("GET List Pages (Async):", response.json())


async def post_list_async(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {
        "address": list_address,
        "description": "Mailgun developers list",
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.create(domain=domain, data=data)
        print("POST List (Async):", response.json())


async def put_list_async(api_key: str, domain: str, list_address: str) -> None:
    """
    PUT /lists/<address> (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {"description": "Mailgun developers list 121212"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.put(domain=domain, data=data, address=list_address)
        print("PUT List (Async):", response.json())


# ==============================================================================
# Mailing List Validation (Asynchronous)
# ==============================================================================


async def delete_list_validation_async(api_key: str, domain: str, list_address: str) -> None:
    """
    DELETE /lists/<address>/validate (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.delete(domain=domain, address=list_address, validate=True)
        print("DELETE List Validation (Async):", response.json())


async def get_list_validation_async(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/validate (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.get(domain=domain, address=list_address, validate=True)
        print("GET List Validation (Async):", response.json())


async def post_list_validation_async(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists/<address>/validate (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists.create(domain=domain, address=list_address, validate=True)
        print("POST List Validation (Async):", response.json())


# ==============================================================================
# Mailing List Members Management (Asynchronous)
# ==============================================================================


async def delete_list_member_async(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    DELETE /lists/<address>/members/<member_address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.delete(
            domain=domain,
            address=list_address,
            member_address=member_address,
        )
        print("DELETE List Member (Async):", response.json())


async def get_list_member_async(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    GET /lists/<address>/members/<member_address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.get(
            domain=domain,
            address=list_address,
            member_address=member_address,
        )
        print("GET List Member (Async):", response.json())


async def get_list_members_async(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/members (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.get(domain=domain, address=list_address)
        print("GET List Members (Async):", response.json())


async def get_list_members_pages_async(api_key: str, domain: str, list_address: str) -> None:
    """
    GET /lists/<address>/members/pages (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members_pages.get(domain=domain, address=list_address)
        print("GET List Members Pages (Async):", response.json())


async def post_list_member_async(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    POST /lists/<address>/members (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "subscribed": True,
        "address": member_address,
        "name": "Bob Bar",
        "description": "Developer",
        "vars": '{"age": 26}',
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.create(domain=domain, address=list_address, data=data)
        print("POST List Member (Async):", response.json())


async def post_list_members_json_async(api_key: str, domain: str, list_address: str) -> None:
    """
    POST /lists/<address>/members.json (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "upsert": True,
        "members": '[{"address": "Alice <alice@example.com>", "vars": {"age": 26}},'
        '{"name": "Bob1", "address": "bob2@example.com", "vars": {"age": 34}}]',
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.create(
            domain=domain,
            address=list_address,
            data=data,
            multiple=True,
        )
        print("POST List Members JSON (Async):", response.json())


async def put_list_member_async(
    api_key: str, domain: str, list_address: str, member_address: str
) -> None:
    """
    PUT /lists/<address>/members/<member_address> (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "subscribed": True,
        "address": member_address,
        "name": "Bob Bar 2",
        "description": "Developer",
        "vars": '{"age": 28}',
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.lists_members.put(
            domain=domain,
            address=list_address,
            data=data,
            member_address=member_address,
        )
        print("PUT List Member (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    # Identifiers mapping to your original business logic
    LIST_ADDRESS_1: str = f"python_sdk2@{DOMAIN}"
    LIST_ADDRESS_2: str = os.environ.get("MAILLIST_ADDRESS", f"my_list@{DOMAIN}")

    MEMBER_ADDRESS_1: str = "bar2@example.com"
    MEMBER_ADDRESS_2: str = "bob2@example.com"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        # Lists Management
        # post_list_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)
        # put_list_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)
        # get_list_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)
        # get_list_pages_sync(api_key=API_KEY, domain=DOMAIN)
        delete_list_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)

        # Lists Validation
        # post_list_validation_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)
        # get_list_validation_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)
        # delete_list_validation_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1)

        # Members Management
        # post_list_member_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2, member_address=MEMBER_ADDRESS_1)
        # post_list_members_json_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2)
        # put_list_member_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2, member_address=MEMBER_ADDRESS_1)
        # get_list_member_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2, member_address=MEMBER_ADDRESS_1)
        # get_list_members_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2)
        # get_list_members_pages_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2)
        # delete_list_member_sync(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2, member_address=MEMBER_ADDRESS_2)

        print("\n--- Running Asynchronous Examples ---")
        # asyncio.run(delete_list_async(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_1))
        # asyncio.run(get_list_member_async(api_key=API_KEY, domain=DOMAIN, list_address=LIST_ADDRESS_2, member_address=MEMBER_ADDRESS_1))

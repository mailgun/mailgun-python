"""Examples for Mailgun Inbox Placement (Optimize) API."""

from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Synchronous Examples (requests)
# ==============================================================================


def post_inbox_sync(api_key: str, domain: str) -> None:
    """
    POST /v3/inbox/tests
    :return: None
    """
    data: dict[str, str] = {
        "domain": domain,
        "from": f"user@{domain}",
        "subject": "testSubject",
        "html": "<html>HTML version of the body</html>",
    }

    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.create(data=data)
        print("POST Inbox Test (Sync):", response.json())


def get_all_inbox_sync(api_key: str) -> None:
    """
    GET /v3/inbox/tests
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.get()
        print("GET All Inbox Tests (Sync):", response.json())


def get_inbox_placement_test_sync(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.get(test_id=test_id)
        print("GET Single Inbox Test (Sync):", response.json())


def inbox_placement_test_counters_sync(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/counters
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.get(test_id=test_id, counters=True)
        print("GET Inbox Test Counters (Sync):", response.json())


def get_inbox_placement_test_checks_sync(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.get(test_id=test_id, checks=True)
        print("GET Inbox Test Checks (Sync):", response.json())


def get_single_placement_check_test_sync(api_key: str, test_id: str, address: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.get(test_id=test_id, checks=True, address=address)
        print("GET Single Placement Check Test (Sync):", response.json())


def delete_inbox_placement_test_sync(api_key: str, test_id: str) -> None:
    """
    DELETE /v3/inbox/tests/<test_id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.inbox_tests.delete(test_id=test_id)
        print("DELETE Inbox Test (Sync):", response.json())


# ==============================================================================
# Asynchronous Examples (httpx)
# ==============================================================================


async def post_inbox_async(api_key: str, domain: str) -> None:
    """
    POST /v3/inbox/tests (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {
        "domain": domain,
        "from": f"async_user@{domain}",
        "subject": "testSubject Async",
        "html": "<html>HTML version of the body</html>",
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.create(data=data)
        print("POST Inbox Test (Async):", response.json())


async def get_all_inbox_async(
    api_key: str,
) -> None:
    """
    GET /v3/inbox/tests (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.get()
        print("GET All Inbox Tests (Async):", response.json())


async def get_inbox_placement_test_async(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.get(test_id=test_id)
        print("GET Single Inbox Test (Async):", response.json())


async def inbox_placement_test_counters_async(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/counters (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.get(test_id=test_id, counters=True)
        print("GET Inbox Test Counters (Async):", response.json())


async def get_inbox_placement_test_checks_async(api_key: str, test_id: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.get(test_id=test_id, checks=True)
        print("GET Inbox Test Checks (Async):", response.json())


async def get_single_placement_check_test_async(api_key: str, test_id: str, address: str) -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.get(test_id=test_id, checks=True, address=address)
        print("GET Single Placement Check Test (Async):", response.json())


async def delete_inbox_placement_test_async(api_key: str, test_id: str) -> None:
    """
    DELETE /v3/inbox/tests/<test_id> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.inbox_tests.delete(test_id=test_id)
        print("DELETE Inbox Test (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    # Dummy identifiers for example purposes
    TEST_ID: str = "123456789"
    TEST_ADDRESS: str = "user@example.com"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        post_inbox_sync(api_key=API_KEY, domain=DOMAIN)
        get_all_inbox_sync(api_key=API_KEY)
        get_inbox_placement_test_sync(api_key=API_KEY, test_id=TEST_ID)
        inbox_placement_test_counters_sync(api_key=API_KEY, test_id=TEST_ID)
        get_inbox_placement_test_checks_sync(api_key=API_KEY, test_id=TEST_ID)
        get_single_placement_check_test_sync(api_key=API_KEY, test_id=TEST_ID, address=TEST_ADDRESS)
        # delete_inbox_placement_test_sync(api_key=API_KEY, test_id=TEST_ID)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(post_inbox_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(get_all_inbox_async(api_key=API_KEY))
        asyncio.run(get_inbox_placement_test_async(api_key=API_KEY, test_id=TEST_ID))
        asyncio.run(inbox_placement_test_counters_async(api_key=API_KEY, test_id=TEST_ID))
        asyncio.run(get_inbox_placement_test_checks_async(api_key=API_KEY, test_id=TEST_ID))
        asyncio.run(
            get_single_placement_check_test_async(
                api_key=API_KEY, test_id=TEST_ID, address=TEST_ADDRESS
            )
        )
        # asyncio.run(delete_inbox_placement_test_async(api_key=API_KEY, test_id=TEST_ID))

"""Examples for managing Mailgun domain SMTP credentials."""

from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Synchronous Examples
# ==============================================================================


def post_credentials_sync(api_key: str, domain: str) -> None:
    """
    POST /domains/<domain>/credentials
    :return: None
    """
    data: dict[str, str] = {
        "login": f"alice_bob@{domain}",
        "password": "test_new_creds123",  # pragma: allowlist secret
    }
    with Client(auth=("api", api_key)) as client:
        response = client.domains_credentials.create(domain=domain, data=data)
        print("POST (Sync):", response.json())


def get_credentials_sync(api_key: str, domain: str) -> None:
    """
    GET /domains/<domain>/credentials
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_credentials.get(domain=domain)
        print("GET (Sync):", response.json())


def put_credentials_sync(api_key: str, domain: str) -> None:
    """
    PUT /domains/<domain>/credentials/<login>
    :return: None
    """
    data: dict[str, str] = {
        "password": "test_new_creds12356"  # pragma: allowlist secret
    }
    with Client(auth=("api", api_key)) as client:
        response = client.domains_credentials.put(
            domain=domain, data=data, login=f"alice_bob@{domain}"
        )
        print("PUT (Sync):", response.json())


def delete_credentials_sync(api_key: str, domain: str) -> None:
    """
    DELETE /domains/<domain>/credentials/<login>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_credentials.delete(domain=domain, login=f"alice_bob@{domain}")
        print("DELETE Single (Sync):", response.json())


def delete_all_domain_credentials_sync(api_key: str, domain: str) -> None:
    """
    DELETE /domains/<domain>/credentials
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_credentials.delete(domain=domain)
        print("DELETE All (Sync):", response.json())


# ==============================================================================
# Asynchronous Examples
# ==============================================================================


async def post_credentials_async(api_key: str, domain: str) -> None:
    """
    POST /domains/<domain>/credentials
    :return: None
    """
    data: dict[str, str] = {
        "login": f"async_alice_bob@{domain}",
        "password": "test_new_creds123",  # pragma: allowlist secret
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_credentials.create(domain=domain, data=data)
        print("POST (Async):", response.json())


async def get_credentials_async(api_key: str, domain: str) -> None:
    """
    GET /domains/<domain>/credentials
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_credentials.get(domain=domain)
        print("GET (Async):", response.json())


async def put_credentials_async(api_key: str, domain: str) -> None:
    """
    PUT /domains/<domain>/credentials/<login>
    :return: None
    """
    data: dict[str, str] = {
        "password": "test_new_creds12356"  # pragma: allowlist secret
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_credentials.put(
            domain=domain, data=data, login=f"async_alice_bob@{domain}"
        )
        print("PUT (Async):", response.json())


async def delete_credentials_async(api_key: str, domain: str) -> None:
    """
    DELETE /domains/<domain>/credentials/<login>
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_credentials.delete(
            domain=domain, login=f"async_alice_bob@{domain}"
        )
        print("DELETE Single (Async):", response.json())


async def delete_all_domain_credentials_async(api_key: str, domain: str) -> None:
    """
    DELETE /domains/<domain>/credentials
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_credentials.delete(domain=domain)
        print("DELETE All (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Credentials Examples ---")
        post_credentials_sync(api_key=API_KEY, domain=DOMAIN)
        get_credentials_sync(api_key=API_KEY, domain=DOMAIN)
        # put_credentials_sync(api_key=API_KEY, domain=DOMAIN)
        # delete_credentials_sync(api_key=API_KEY, domain=DOMAIN)
        # delete_all_domain_credentials_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Credentials Examples ---")
        asyncio.run(post_credentials_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(get_credentials_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(put_credentials_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(delete_credentials_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(delete_all_domain_credentials_async(api_key=API_KEY, domain=DOMAIN))

"""Examples for managing Mailgun Dedicated IPs and Domain IP assignments."""

from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Dedicated IP Management (Synchronous)
# ==============================================================================


def get_ips_sync(api_key: str, domain: str) -> None:
    """
    GET /ips
    :return: None
    """
    filters: dict[str, str] = {"dedicated": "true"}
    with Client(auth=("api", api_key)) as client:
        response = client.ips.get(domain=domain, filters=filters)
        print("GET IPs (Sync):", response.json())


def get_single_ip_sync(api_key: str, domain: str, target_ip: str) -> None:
    """
    GET /ips/<ip>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.ips.get(domain=domain, ip=target_ip)
        print("GET Single IP (Sync):", response.json())


# ==============================================================================
# Domain IP Linkage (Synchronous)
# ==============================================================================


def get_domain_ips_sync(api_key: str, domain: str) -> None:
    """
    GET /domains/<domain>/ips
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_ips.get(domain=domain)
        print("GET Domain IPs (Sync):", response.json())


def post_domains_ip_sync(api_key: str, domain: str, target_ip: str) -> None:
    """
    POST /domains/<domain>/ips
    :return: None
    """
    data: dict[str, str] = {"ip": target_ip}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_ips.create(domain=domain, data=data)
        print("POST Domain IP (Sync):", response.json())


def delete_domain_ip_sync(api_key: str, domain: str, target_ip: str) -> None:
    """
    DELETE /domains/<domain>/ips/<ip>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_ips.delete(domain=domain, ip=target_ip)
        print("DELETE Domain IP (Sync):", response.json())


# ==============================================================================
# Dedicated IP Management (Asynchronous)
# ==============================================================================


async def get_ips_async(api_key: str, domain: str) -> None:
    """
    GET /ips (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"dedicated": "true"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ips.get(domain=domain, filters=filters)
        print("GET IPs (Async):", response.json())


async def get_single_ip_async(api_key: str, domain: str, target_ip: str) -> None:
    """
    GET /ips/<ip> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.ips.get(domain=domain, ip=target_ip)
        print("GET Single IP (Async):", response.json())


# ==============================================================================
# Domain IP Linkage (Asynchronous)
# ==============================================================================


async def get_domain_ips_async(api_key: str, domain: str) -> None:
    """
    GET /domains/<domain>/ips (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_ips.get(domain=domain)
        print("GET Domain IPs (Async):", response.json())


async def post_domains_ip_async(api_key: str, domain: str, target_ip: str) -> None:
    """
    POST /domains/<domain>/ips (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {"ip": target_ip}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_ips.create(domain=domain, data=data)
        print("POST Domain IP (Async):", response.json())


async def delete_domain_ip_async(api_key: str, domain: str, target_ip: str) -> None:
    """
    DELETE /domains/<domain>/ips/<ip> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domains_ips.delete(domain=domain, ip=target_ip)
        print("DELETE Domain IP (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    # Dummy identifier for example purposes
    TARGET_IP: str = "1.2.3.4"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_ips_sync(api_key=API_KEY, domain=DOMAIN)
        # get_single_ip_sync(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP)
        # get_domain_ips_sync(api_key=API_KEY, domain=DOMAIN)
        # post_domains_ip_sync(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP)
        # delete_domain_ip_sync(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(get_ips_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(get_single_ip_async(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP))
        # asyncio.run(get_domain_ips_async(api_key=API_KEY, domain=DOMAIN))
        # asyncio.run(post_domains_ip_async(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP))
        # asyncio.run(delete_domain_ip_async(api_key=API_KEY, domain=DOMAIN, target_ip=TARGET_IP))

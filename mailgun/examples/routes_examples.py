"""Examples for managing Mailgun Routes."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Routes Management (Synchronous)
# ==============================================================================


def delete_route_sync(api_key: str, domain: str, route_id: str) -> None:
    """
    DELETE /routes/<id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.routes.delete(domain=domain, route_id=route_id)
        print("DELETE Route (Sync):", response.json())


def get_route_by_id_sync(api_key: str, domain: str, route_id: str) -> None:
    """
    GET /routes/<id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.routes.get(domain=domain, route_id=route_id)
        print("GET Route By ID (Sync):", response.json())


def get_routes_match_sync(api_key: str, domain: str, sender: str) -> None:
    """
    GET /routes/match
    :return: None
    """
    filters: dict[str, str] = {"address": sender}
    with Client(auth=("api", api_key)) as client:
        response = client.routes_match.get(domain=domain, filters=filters)
        print("GET Routes Match (Sync):", response.json())


def get_routes_sync(api_key: str, domain: str) -> None:
    """
    GET /routes
    :return: None
    """
    filters: dict[str, int] = {"skip": 0, "limit": 1}
    with Client(auth=("api", api_key)) as client:
        response = client.routes.get(domain=domain, filters=filters)
        print("GET Routes (Sync):", response.json())


def post_routes_sync(api_key: str, domain: str) -> None:
    """
    POST /routes
    :return: None
    """
    data: dict[str, Any] = {
        "priority": 0,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.routes.create(domain=domain, data=data)
        print("POST Routes (Sync):", response.json())


def put_route_sync(api_key: str, domain: str, route_id: str) -> None:
    """
    PUT /routes/<id>
    :return: None
    """
    data: dict[str, Any] = {
        "priority": 2,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.routes.put(domain=domain, data=data, route_id=route_id)
        print("PUT Route (Sync):", response.json())


# ==============================================================================
# Routes Management (Asynchronous)
# ==============================================================================


async def delete_route_async(api_key: str, domain: str, route_id: str) -> None:
    """
    DELETE /routes/<id> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes.delete(domain=domain, route_id=route_id)
        print("DELETE Route (Async):", response.json())


async def get_route_by_id_async(api_key: str, domain: str, route_id: str) -> None:
    """
    GET /routes/<id> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes.get(domain=domain, route_id=route_id)
        print("GET Route By ID (Async):", response.json())


async def get_routes_async(api_key: str, domain: str) -> None:
    """
    GET /routes (Asynchronous)
    :return: None
    """
    filters: dict[str, int] = {"skip": 0, "limit": 1}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes.get(domain=domain, filters=filters)
        print("GET Routes (Async):", response.json())


async def get_routes_match_async(api_key: str, domain: str, sender: str) -> None:
    """
    GET /routes/match (Asynchronous)
    :return: None
    """
    filters: dict[str, str] = {"address": sender}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes_match.get(domain=domain, filters=filters)
        print("GET Routes Match (Async):", response.json())


async def post_routes_async(api_key: str, domain: str) -> None:
    """
    POST /routes (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "priority": 0,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes.create(domain=domain, data=data)
        print("POST Routes (Async):", response.json())


async def put_route_async(api_key: str, domain: str, route_id: str) -> None:
    """
    PUT /routes/<id> (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "priority": 2,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.routes.put(domain=domain, data=data, route_id=route_id)
        print("PUT Route (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")
    SENDER: str = os.environ.get("MESSAGES_FROM", "sender@example.com")

    ROUTE_ID_1: str = "1234567890"
    ROUTE_ID_2: str = "0987654321"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        get_routes_match_sync(api_key=API_KEY, domain=DOMAIN, sender=SENDER)
        # get_routes_sync(api_key=API_KEY, domain=DOMAIN)
        # get_route_by_id_sync(api_key

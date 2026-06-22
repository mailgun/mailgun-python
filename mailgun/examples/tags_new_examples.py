"""Examples for managing Mailgun Analytics Tags (New)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mailgun.client import AsyncClient, Client


# ==============================================================================
# Analytics Tags Management (Synchronous)
# ==============================================================================


def delete_analytics_tags_sync(api_key: str, tag_name: str) -> None:
    """
    # Metrics
    # DELETE /v1/analytics/tags
    :return: None
    """
    data: dict[str, str] = {"tag": tag_name}
    with Client(auth=("api", api_key)) as client:
        response = client.analytics_tags.delete(data=data)
        print("DELETE Analytics Tags (Sync):", response.json())


def get_account_analytics_tag_limit_information_sync(api_key: str) -> None:
    """
    # Metrics
    # GET /v1/analytics/tags/limits
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.analytics_tags_limits.get()
        print("GET Analytics Tag Limits (Sync):", response.json())


def post_analytics_tags_sync(api_key: str) -> None:
    """
    # Metrics
    # POST /v1/analytics/tags
    :return: None
    """
    data: dict[str, Any] = {
        "pagination": {"sort": "lastseen:desc", "limit": 10},
        "include_subaccounts": True,
    }
    with Client(auth=("api", api_key)) as client:
        response = client.analytics_tags.create(data=data)
        print("POST Analytics Tags (Sync):", response.json())


def update_analytics_tags_sync(api_key: str, tag_name: str, description: str) -> None:
    """
    # Metrics
    # PUT /v1/analytics/tags
    :return: None
    """
    data: dict[str, str] = {
        "tag": tag_name,
        "description": description,
    }
    with Client(auth=("api", api_key)) as client:
        response = client.analytics_tags.update(data=data)
        print("PUT Analytics Tags (Sync):", response.json())


# ==============================================================================
# Analytics Tags Management (Asynchronous)
# ==============================================================================


async def delete_analytics_tags_async(api_key: str, tag_name: str) -> None:
    """
    # Metrics
    # DELETE /v1/analytics/tags (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {"tag": tag_name}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_tags.delete(data=data)
        print("DELETE Analytics Tags (Async):", response.json())


async def get_account_analytics_tag_limit_information_async(api_key: str) -> None:
    """
    # Metrics
    # GET /v1/analytics/tags/limits (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_tags_limits.get()
        print("GET Analytics Tag Limits (Async):", response.json())


async def post_analytics_tags_async(api_key: str) -> None:
    """
    # Metrics
    # POST /v1/analytics/tags (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "pagination": {"sort": "lastseen:desc", "limit": 10},
        "include_subaccounts": True,
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_tags.create(data=data)
        print("POST Analytics Tags (Async):", response.json())


async def update_analytics_tags_async(api_key: str, tag_name: str, description: str) -> None:
    """
    # Metrics
    # PUT /v1/analytics/tags (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {
        "tag": tag_name,
        "description": description,
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.analytics_tags.update(data=data)
        print("PUT Analytics Tags (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")

    TAG_NAME_TO_DELETE: str = "name-of-tag-to-delete"
    TAG_NAME_TO_UPDATE: str = "name-of-tag-to-update"
    UPDATED_DESCRIPTION: str = "updated tag description"

    if not API_KEY:
        print("Please set the 'APIKEY' environment variable to run examples.")
    else:
        print("--- Running Synchronous Examples ---")
        post_analytics_tags_sync(api_key=API_KEY)
        update_analytics_tags_sync(
            api_key=API_KEY, tag_name=TAG_NAME_TO_UPDATE, description=UPDATED_DESCRIPTION
        )
        delete_analytics_tags_sync(api_key=API_KEY, tag_name=TAG_NAME_TO_DELETE)
        get_account_analytics_tag_limit_information_sync(api_key=API_KEY)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(post_analytics_tags_async(api_key=API_KEY))
        asyncio.run(
            update_analytics_tags_async(
                api_key=API_KEY, tag_name=TAG_NAME_TO_UPDATE, description=UPDATED_DESCRIPTION
            )
        )
        asyncio.run(delete_analytics_tags_async(api_key=API_KEY, tag_name=TAG_NAME_TO_DELETE))
        asyncio.run(get_account_analytics_tag_limit_information_async(api_key=API_KEY))

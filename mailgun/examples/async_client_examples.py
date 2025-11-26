from __future__ import annotations

import asyncio
import os

from mailgun.client import AsyncClient


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: AsyncClient = AsyncClient(auth=("api", key))


async def get_credentials() -> None:
    """
    GET /domains/<domain>/credentials
    :return:
    """
    request = await client.domains_credentials.get(domain=domain)
    print(request.json())


async def get_single_validate() -> None:
    """
    GET /v4/address/validate
    :return:
    """
    params = {"address": "test@gmail.com", "provider_lookup": "false"}
    req = await client.addressvalidate.get(domain=domain, filters=params)
    print(req.json())


# context manager approach examples:
async def view_message_with_storage_url() -> None:
    """
    /v3/domains/2048.zeefarmer.com/messages/{storage_url}
    :return:
    """
    params = {"limit": 1}

    storage_url = client.events.get(domain=domain, filters=params).json()["items"][0]["storage"][
        "url"
    ]
    async with AsyncClient(auth=("api", key)) as _client:
        req = await _client.domains_messages.get(domain=domain, api_storage_url=storage_url)
    print(req.json())


async def post_inbox() -> None:
    """
    POST /v3/inbox/tests
    :return:
    """
    data = {
        "domain": "domain.com",
        "from": "user@sending_domain.com",
        "subject": "testSubject",
        "html": "<html>HTML version of the body</html>",
    }
    async with AsyncClient(auth=("api", key)) as _client:
        req = client.inbox_tests.create(domain=domain, data=data)
    print(req.json())


if __name__ == "__main__":
    coroutines = [
        get_single_validate(),
        get_credentials(),
        view_message_with_storage_url(),
        post_inbox(),
    ]
    asyncio.gather(*coroutines)

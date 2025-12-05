from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_users() -> None:
    """
    GET /v5/users
    :return:
    """
    query = {"role": "admin", "limit": "0", "skip": "0"}
    req = client.users.get(filters=query)
    print(req)
    print(req.json())


def get_user_details() -> None:
    """
    GET /v5/users/{user_id}
    :return:
    """
    user_id = "xxxxxxxxxxxxxxxxxxxxxxxx"
    req = client.users.get(user_id=user_id)
    print(req)
    print(req.json())


if __name__ == "__main__":
    get_users()
    get_user_details()

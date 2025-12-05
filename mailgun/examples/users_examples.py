from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
mailgun_email = os.environ["MAILGUN_EMAIL"]

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
    query = {"role": "admin", "limit": "0", "skip": "0"}
    req1 = client.users.get(filters=query)
    users = req1.json()["users"]

    for user in users:
        if mailgun_email == user["email"]:
            req2 = client.users.get(user_id=user["id"])
            print(req2)
            print(req2.json())


if __name__ == "__main__":
    get_users()
    get_user_details()

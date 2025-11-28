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


# TODO: HTTP/2 403 {"message":"Incompatible key for this endpoint"}
# def get_own_user_details() -> None:
#     """
#     GET /v5/users/me
#     :return:
#     """
#     user_id = "me"
#     req = client.users.get(user_id=user_id)
#     print(req)
#     print(req.json())


# TODO: HTTP/2 400 {'message': "User's account USER_ID is not in the organization ORG_ID"}
# def add_user_to_org() -> None:
#     """
#     PUT /v5/users/{user_id}/org/{org_id}
#     :return:
#     """
#     user_id = "xxxxxxxxxxxxxxxxxxxxxxxx"
#     org_id = "on.sinch.com"
#     req = client.users_org.put(user_id=user_id, org_id=org_id)
#     print(req)
#     print(req.json())

if __name__ == "__main__":
    get_users()
    get_user_details()

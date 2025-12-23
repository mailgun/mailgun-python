from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
mailgun_email = os.environ["MAILGUN_EMAIL"]
role = os.environ["ROLE"]
user_id = os.environ["USER_ID"]
user_name = os.environ["USER_NAME"]

client: Client = Client(auth=("api", key))


def get_keys() -> None:
    """
    GET /v1/keys
    :return:
    """
    query = {"domain_name": "python.test.domain5", "kind": "web"}
    req = client.keys.get(filters=query)
    print(req.json())


def post_keys() -> None:
    """
    POST /v1/keys

    This code generate a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID  values.
    This is returned by the API in the "secret":"API_KEY" key/value pair. This key will authenticate the call (Get one's own user details) made to the /v5/users/me endpoint,   # pragma: allowlist secret
    and will return the user's data associated with the USER_EMAIL and USER_ID values.

    Important Notes:
    USER_EMAIL - The user login email address of the user that is trying to make the call to the /v5/users/me endpoint.
    SECONDS - How many seconds you want the key to be active before it expires.
    ROLE - The role of the API Key. This dictates what permissions the key has (https://help.mailgun.com/hc/en-us/articles/26016288026907-API-Key-Roles)
    USER_ID - The internal User ID of the user that is trying to call the /v5/users/me endpoint. This is present in the URL in the address bar when viewing the User details in the GUI or in Admin. Both will show /users/USER_ID in the address.
    DESCRIPTION - Description of the key.

    :return:
    """

    data = {
        "email": mailgun_email,
        "domain_name": "python.test.domain5",
        "kind": "web",
        "expiration": "3600",
        "role": role,
        "user_id": user_id,
        "user_name": user_name,
        "description": "a new key",
    }

    headers = {"Content-Type": "multipart/form-data"}

    req = client.keys.create(data=data, headers=headers)
    print(req.json())


def delete_key() -> None:
    """
    DELETE /vq/keys/{key_id}
    :return:
    """
    query = {"domain_name": "python.test.domain5", "kind": "web"}
    req1 = client.keys.get(filters=query)
    items = req1.json()["items"]

    for item in items:
        if mailgun_email == item["requestor"]:  # codespell:disable-line
            req2 = client.keys.delete(key_id=item["id"])
            print(req2.json())


def regenerate_key() -> None:
    """
    POST /v1/keys/public
    :return:
    """
    req = client.keys_public.create()
    print(req.json())


if __name__ == "__main__":
    # get_keys()
    post_keys()
    get_keys()
    delete_key()
    get_keys()
    regenerate_key()
    get_keys()

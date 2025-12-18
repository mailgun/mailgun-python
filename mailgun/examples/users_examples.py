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


def get_users() -> None:
    """
    GET /v5/users
    :return:
    """
    query = {"role": role, "limit": "0", "skip": "0"}
    req = client.users.get(filters=query)
    print(req.json())


def get_own_user_details() -> None:
    """
    GET /v5/users/me

    Please note, for the command("Get one's own user details") to be successful, you must use a Web type API key for the call. Private type API keys will Not work.
    The below Call will generate a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID  values.
    This is returned by the API in the "secret":"API_KEY" key/value pair.  # pragma: allowlist secret
    This key will authenticate the call(Get one's own user details) made to the /v5/users/me endpoint, and will return the user's data associated with the USER_EMAIL and USER_ID values.

    see https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/keys/api.(*keysapi).createkey-fm-7

    Important Notes:
    API_KEY - Private API Key
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

    req1 = client.keys.create(data=data, headers=headers)
    print(req1.json())
    secret = req1.json()["key"]["secret"]

    client_with_secret_key: Client = Client(auth=("api", secret))
    req2 = client_with_secret_key.users.get(user_id="me")
    print(req2.json())


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
            print(req2.json())


if __name__ == "__main__":
    get_users()
    get_own_user_details()
    get_user_details()

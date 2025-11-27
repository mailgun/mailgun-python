from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_credentials() -> None:
    """
    GET /domains/<domain>/credentials
    :return:
    """
    request = client.domains_credentials.get(domain=domain)
    print(request.json())


def post_credentials() -> None:
    """
    POST /domains/<domain>/credentials
    :return:
    """
    data = {
        "login": f"alice_bob@{domain}",
        "password": "test_new_creds123",  # pragma: allowlist secret
    }
    request = client.domains_credentials.create(domain=domain, data=data)
    print(request.json())


def put_credentials() -> None:
    """
    PUT /domains/<domain>/credentials/<login>
    :return:
    """
    data = {"password": "test_new_creds12356"}  # pragma: allowlist secret
    request = client.domains_credentials.put(domain=domain, data=data, login=f"alice_bob@{domain}")
    print(request.json())


def put_mailboxes_credentials() -> None:
    """
    PUT /v3/{domain_name}/mailboxes/{spec}
    :return:
    """

    req = client.mailboxes.put(domain=domain, login=f"alice_bob@{domain}")
    print(req)
    print(req.json())


def delete_all_domain_credentials() -> None:
    """
    DELETE /domains/<domain>/credentials
    :return:
    """
    request = client.domains_credentials.delete(domain=domain)
    print(request.json())


def delete_credentials() -> None:
    """
    DELETE /domains/<domain>/credentials/<login>
    :return:
    """
    request = client.domains_credentials.delete(domain=domain, login=f"alice_bob@{domain}")
    print(request.json())

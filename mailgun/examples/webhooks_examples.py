from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_webhooks() -> None:
    """
    GET /domains/<domain>/webhooks
    :return:
    """
    req = client.domains_webhooks.get(domain=domain)
    print(req.json())


def create_webhook() -> None:
    """
    POST /domains/<domain>/webhooks
    :return:
    """
    data = {"id": "clicked", "url": ["https://facebook.com"]}
    #
    req = client.domains_webhooks.create(domain=domain, data=data)
    print(req.json())


def get_webhook() -> None:
    """
    GET /domains/<domain>/webhooks/<webhookname>
    :return:
    """
    req = client.domains_webhooks_clicked.get(domain=domain)
    print(req.json())


def put_webhook() -> None:
    """
    PUT /domains/<domain>/webhooks/<webhookname>
    :return:
    """
    data = {"id": "clicked", "url": ["https://facebook.com", "https://google.com"]}

    req = client.domains_webhooks_clicked.put(domain=domain, data=data)
    print(req.json())


def delete_webhook() -> None:
    """
    DELETE /domains/<domain>/webhooks/<webhookname>
    :return:
    """
    req = client.domains_webhooks_clicked.delete(domain=domain)
    print(req.json())


if __name__ == "__main__":
    get_webhooks()

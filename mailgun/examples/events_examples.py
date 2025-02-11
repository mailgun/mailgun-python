import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_domain_events() -> None:
    """
    GET /<domain>/events
    :return:
    """
    req = client.events.get(domain=domain)
    print(req.json())


def view_message_with_storage_url() -> None:
    """
    /v3/domains/2048.zeefarmer.com/messages/{storage_url}
    :return:
    """
    params = {"limit": 1}

    storage_url = client.events.get(domain=domain, filters=params).json()["items"][0][
        "storage"
    ]["url"]
    req = client.domains_messages.get(domain=domain, api_storage_url=storage_url)
    print(req.json())


def events_by_recipient() -> None:
    """
    GET /<domain>/events
    :return:
    """
    params = {
        "begin": "Tue, 24 Nov 2020 09:00:00 -0000",
        "ascending": "yes",
        "limit": 10,
        "pretty": "yes",
        "recipient": os.environ["VALIDATION_ADDRESS_1"],
    }
    req = client.events.get(domain=domain, filters=params)
    print(req.json())


def events_rejected_or_failed() -> None:
    """
    GET /<domain>/events
    :return:
    """
    params = {"event": "rejected OR failed"}
    req = client.events.get(domain=domain, filters=params)
    print(req.json())


if __name__ == "__main__":
    events_rejected_or_failed()

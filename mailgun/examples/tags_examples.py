import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_tags() -> None:
    """
    GET /<domain>/tags
    :return:
    """
    req = client.tags.get(domain=domain)
    print(req.json())


def get_single_tag() -> None:
    """
    GET /<domain>/tags/<tag>
    :return:
    """
    req = client.tags.get(domain=domain, tag_name="Python test")
    print(req.json())


def put_single_tag() -> None:
    """
    PUT /<domain>/tags/<tag>
    :return:
    """
    data = {"description": "Python testtt"}

    req = client.tags.put(domain=domain, tag_name="Python test", data=data)
    print(req.json())


def get_tag_stats() -> None:
    """
    GET /<domain>/tags/<tag>/stats
    :return:
    """
    params = {"event": "accepted"}
    req = client.tags_stats.get(domain=domain, filters=params, tag_name="Python test")
    print(req.json())


def delete_tag() -> None:
    """
    DELETE /<domain>/tags/<tag>
    :return:
    """
    req = client.tags.delete(domain=domain, tag_name="Python test")
    print(req.json())


def get_aggregate_countries() -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/countries
    :return:
    """
    req = client.tags_stats_aggregates_countries.get(
        domain=domain, tag_name="September newsletter"
    )
    print(req.json())


def get_aggregate_providers() -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/providers
    :return:
    """
    req = client.tags_stats_aggregates_providers.get(
        domain=domain, tag_name="September newsletter"
    )
    print(req.json())


def get_aggregate_devices() -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/devices
    :return:
    """
    req = client.tags_stats_aggregates_devices.get(
        domain=domain, tag_name="September newsletter"
    )
    print(req.json())


if __name__ == "__main__":
    get_aggregate_devices()

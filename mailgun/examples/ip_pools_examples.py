import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_ippools() -> None:
    """
    GET /v1/ip_pools
    :return:
    """
    req = client.ippools.get(domain=domain)
    print(req.json())


def create_ippool() -> None:
    """
    POST /v1/ip_pools
    :return:
    """
    post_data = {"name": "test_pool1", "description": "Test", "ips": ["166.78.68.186"]}
    req_post = client.ippools.create(domain=domain, data=post_data)
    print(req_post.json())


def update_ippool() -> None:
    """
    PATCH /v1/ip_pools/{pool_id}
    :return:
    """
    data = {
        "name": "test_pool3",
        "description": "Test3",
    }
    req = client.ippools.patch(
        domain=domain, data=data, pool_id="60140bc1fee3e84dec5abeeb"
    )
    print(req.json())


def delete_ippool() -> None:
    """
    DELETE /v1/ip_pools/{pool_id}
    :return:
    """
    req = client.ippools.delete(domain=domain, pool_id="60140bc1fee3e84dec5abeeb")
    print(req.json())


def link_ippool() -> None:
    """
    POST /v3/domains/{domain_name}/ips
    :return:
    """
    data = {"pool_id": "60140d220859fda7bab8bb6c"}
    req = client.domains_ips.create(domain=domain, data=data)
    print(req.json())


def unlink_ippool() -> None:
    """
    DELETE /v3/domains/{domain_name}/ips/ip_pool
    :return:
    """
    data = {"pool_id": "5ff37204e5eb74149462c375"}

    req = client.domains_ips.delete(domain=domain, filters=data, unlink_pool=True)
    print(req.json())


if __name__ == "__main__":
    get_ippools()

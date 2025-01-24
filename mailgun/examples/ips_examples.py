import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_ips() -> None:
    """
    GET /ips
    :return:
    """
    req = client.ips.get(domain=domain, filters={"dedicated": "true"})
    print(req.json())


def get_single_ip() -> None:
    """
    GET /ips/<ip>
    :return:
    """
    req = client.ips.get(domain=domain, ip="161.38.194.10")
    print(req.json())


def get_domain_ips() -> None:
    """
    GET /domains/<domain>/ips
    :return:
    """
    request = client.domains_ips.get(domain=domain)
    print(request.json())


def post_domains_ip() -> None:
    """
    POST /domains/<domain>/ips
    :return:
    """
    ip_data = {"ip": "161.38.194.10"}
    request = client.domains_ips.create(domain=domain, data=ip_data)
    print(request.json())


def delete_domain_ip() -> None:
    """
    DELETE /domains/<domain>/ips/<ip>
    :return:
    """
    request = client.domains_ips.delete(domain=domain, ip="161.38.194.10")
    print(request.json())


if __name__ == "__main__":
    get_ips()

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
sender: str = os.environ["MESSAGES_FROM"]

client: Client = Client(auth=("api", key))


def get_routes() -> None:
    """
    GET /routes
    :return:
    """
    params = {"skip": 0, "limit": 1}
    req = client.routes.get(domain=domain, filters=params)
    print(req.json())


def get_route_by_id() -> None:
    """
    GET /routes/<id>
    :return:
    """
    req = client.routes.get(domain=domain, route_id="6012d994e8d489e24a127e79")
    print(req.json())


def post_routes() -> None:
    """
    POST /routes
    :return:
    """
    data = {
        "priority": 0,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    req = client.routes.create(domain=domain, data=data)
    print(req.json())


def put_route() -> None:
    """
    PUT /routes/<id>
    :return:
    """
    data = {
        "priority": 2,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    req = client.routes.put(domain=domain, data=data, route_id="60142b357c90c3c9f228e0a6")
    print(req.json())


def delete_route() -> None:
    """
    DELETE /routes/<id>
    :return:
    """
    req = client.routes.delete(domain=domain, route_id="60142b357c90c3c9f228e0a6")
    print(req.json())


def get_routes_match() -> None:
    """
    GET /routes/match
    :return:
    """
    query = {"address": sender}
    req = client.routes_match.get(domain=domain, filters=query)
    print(req.json())


if __name__ == "__main__":
    get_routes_match()

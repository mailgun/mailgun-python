import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_stats_total() -> None:
    params = {"event": ["accepted", "delivered", "failed"], "duration": "1m"}

    req = client.stats_total.get(filters=params, domain=domain)
    print(req.json())


if __name__ == "__main__":
    get_stats_total()

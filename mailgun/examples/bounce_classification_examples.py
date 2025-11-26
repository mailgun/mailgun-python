import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def post_list_statistic_v2() -> None:
    """
    # Bounce Classification
    # POST /v2/bounce-classification/metrics
    :return:
    """

    payload = {
        "start": "Wed, 12 Nov 2025 23:00:00 UTC",
        "end": "Thu, 13 Nov 2025 23:00:00 UTC",
        "resolution": "day",
        "duration": "24h0m0s",
        "dimensions": ["entity-name", "domain.name"],
        "metrics": [
            "critical_bounce_count",
            "non_critical_bounce_count",
            "critical_delay_count",
            "non_critical_delay_count",
            "delivered_smtp_count",
            "classified_failures_count",
            "critical_bounce_rate",
            "non_critical_bounce_rate",
            "critical_delay_rate",
            "non_critical_delay_rate",
        ],
        "filter": {
            "AND": [
                {
                    "attribute": "domain.name",
                    "comparator": "=",
                    "values": [{"value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "pagination": {"sort": "entity-name:asc", "limit": 10},
    }

    headers = {"Content-Type": "application/json"}

    req = client.bounceclassification_metrics.create(data=payload, headers=headers)
    print(req.json())


if __name__ == "__main__":
    post_list_statistic_v2()

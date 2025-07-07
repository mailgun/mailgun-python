import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def post_analytics_metrics() -> None:
    """
    # Metrics
    # POST /analytics/metrics
    :return:
    """

    data = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": ["accepted_count", "delivered_count", "clicked_rate", "opened_rate"],
        "filter": {
            "AND": [
                {
                    "attribute": "domain",
                    "comparator": "=",
                    "values": [{"label": domain, "value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "include_aggregates": True,
    }

    req = client.analytics_metrics.create(data=data)
    print(req.json())


def post_analytics_usage_metrics() -> None:
    """
    # Usage Metrics
    # POST /analytics/usage/metrics
    :return:
    """
    data = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": [
            "accessibility_count",
            "accessibility_failed_count",
            "domain_blocklist_monitoring_count",
            "email_preview_count",
            "email_preview_failed_count",
            "email_validation_bulk_count",
            "email_validation_count",
            "email_validation_list_count",
            "email_validation_mailgun_count",
            "email_validation_mailjet_count",
            "email_validation_public_count",
            "email_validation_single_count",
            "email_validation_valid_count",
            "image_validation_count",
            "image_validation_failed_count",
            "ip_blocklist_monitoring_count",
            "link_validation_count",
            "link_validation_failed_count",
            "processed_count",
            "seed_test_count",
        ],
        "include_subaccounts": True,
        "include_aggregates": True,
    }

    req = client.analytics_usage_metrics.create(data=data)
    print(req.json())


if __name__ == "__main__":
    post_analytics_metrics()
    post_analytics_usage_metrics()

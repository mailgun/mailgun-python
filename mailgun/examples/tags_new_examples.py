import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def post_analytics_tags() -> None:
    """
    # Metrics
    # POST /v1/analytics/tags
    :return:
    """

    data = {
        "pagination": {"sort": "lastseen:desc", "limit": 10},
        "include_subaccounts": True,
    }

    req = client.analytics_tags.create(data=data)
    print(req.json())


def update_analytics_tags() -> None:
    """
    # Metrics
    # PUT /v1/analytics/tags
    :return:
    """

    data = {
        "tag": "name-of-tag-to-update",
        "description": "updated tag description",
    }

    req = client.analytics_tags.update(data=data)
    print(req.json())


def delete_analytics_tags() -> None:
    """
    # Metrics
    # DELETE /v1/analytics/tags
    :return:
    """

    data = {"tag": "name-of-tag-to-delete"}

    req = client.analytics_tags.delete(data=data)
    print(req.json())


def get_account_analytics_tag_limit_information() -> None:
    """
    # Metrics
    # GET /v1/analytics/tags/limits
    :return:
    """

    req = client.analytics_tags_limits.get()
    print(req.json())


if __name__ == "__main__":
    post_analytics_tags()
    update_analytics_tags()
    delete_analytics_tags()
    get_account_analytics_tag_limit_information()

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def post_inbox() -> None:
    """
    POST /v3/inbox/tests
    :return:
    """
    data = {
        "domain": "domain.com",
        "from": "user@sending_domain.com",
        "subject": "testSubject",
        "html": "<html>HTML version of the body</html>",
    }

    req = client.inbox_tests.create(domain=domain, data=data)
    print(req.json())


def get_all_inbox() -> None:
    """
    GET /v3/inbox/tests
    :return:
    """
    req = client.inbox_tests.get(domain=domain)
    print(req.json())


def get_inbox_placement_test() -> None:
    """
    GET /v3/inbox/tests/<test_id>
    :return:
    """
    req = client.inbox_tests.get(domain=domain, test_id="6017b5cf3c92d93bd1f810ea")
    print(req.json())


def delete_inbox_placement_test() -> None:
    """
    DELETE /v3/inbox/tests/<test_id>
    :return:
    """
    req = client.inbox_tests.delete(domain=domain, test_id="6017b5cf3c92d93bd1f810ea")
    print(req.json())


def inbox_placement_test_counters() -> None:
    """
    GET /v3/inbox/tests/<test_id>/counters
    :return:
    """
    req = client.inbox_tests.get(
        domain=domain, test_id="6017b5cf3c92d93bd1f810ea", counters=True
    )
    print(req.json())


def get_inbox_placement_test_checks() -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks
    :return:
    """
    req = client.inbox_tests.get(
        domain=domain, test_id="6017b5cf3c92d93bd1f810ea", checks=True
    )
    print(req.json())


def get_single_placement_check_test() -> None:
    """
    GET /v3/inbox/tests/<test_id>/checks/<address>
    :return:
    """
    req = client.inbox_tests.get(
        domain=domain,
        test_id="6017b5cf3c92d93bd1f810ea",
        checks=True,
        address="aa_ext_test03mg@comcast.net",
    )
    print(req.json())


if __name__ == "__main__":
    get_single_placement_check_test()

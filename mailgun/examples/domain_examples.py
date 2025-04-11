from __future__ import annotations

import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_domains() -> None:
    """
    GET /domains
    :return:
    """
    data = client.domainlist.get()
    print(data.json())


def add_domain() -> None:
    """
    POST /domains
    :return:
    """
    # Post domain
    data = {
        "name": "python.test.domain5",
        # "smtp_password": "cisco123456"
    }
    # Problem with smtp_password!!!!

    request = client.domains.create(data=data)
    print(request.json())
    print(request.status_code)


# Get domain


def get_simple_domain() -> None:
    """
    GET /domains/<domain>
    :return:
    """
    domain_name = "python.test.domain5"
    request = client.domains.get(domain_name=domain_name)
    print(request.json())


def update_simple_domain() -> None:
    """
    PUT /domains/<domain>
    :return:
    """
    domain_name = "python.test.domain5"
    data = {"name": domain_name, "spam_action": "disabled"}
    request = client.domains.put(data=data, domain=domain_name)
    print(request.json())


def verify_domain() -> None:
    """
    PUT /domains/<domain>/verify
    :return:
    """
    domain_name = "python.test.domain5"
    request = client.domains.put(domain=domain_name, verify=True)
    print(request.json())


def delete_domain() -> None:
    """
    DELETE /domains/<domain>
    :return:
    """
    # Delete domain
    request = client.domains.delete(domain="python.test.domain5")
    print(request.text)
    print(request.status_code)


def get_credentials() -> None:
    """
    GET /domains/<domain>/credentials
    :return:
    """
    request = client.domains_credentials.get(domain=domain)
    print(request.json())


def post_credentials() -> None:
    """
    POST /domains/<domain>/credentials
    :return:
    """
    data = {"login": f"alice_bob@{domain}", "password": "test_new_creds123"}
    request = client.domains_credentials.create(domain=domain, data=data)
    print(request.json())


def put_credentials() -> None:
    """
    PUT /domains/<domain>/credentials/<login>
    :return:
    """
    data = {"password": "test_new_creds12356"}
    request = client.domains_credentials.put(
        domain=domain, data=data, login=f"alice_bob@{domain}"
    )
    print(request.json())


def delete_all_domain_credentials() -> None:
    """
    DELETE /domains/<domain>/credentials
    :return:
    """
    request = client.domains_credentials.delete(domain=domain)
    print(request.json())


def delete_credentials() -> None:
    """
    DELETE /domains/<domain>/credentials/<login>
    :return:
    """
    request = client.domains_credentials.delete(
        domain=domain, login=f"alice_bob@{domain}"
    )
    print(request.json())


def get_connections() -> None:
    """
    GET /domains/<domain>/connection
    :return:
    """
    request = client.domains_connection.get(domain=domain)
    print(request.json())


def put_connections() -> None:
    """
    PUT /domains/<domain>/connection
    :return:
    """
    data = {"require_tls": "true", "skip_verification": "false"}
    request = client.domains_connection.put(domain=domain, data=data)
    print(request.json())


def get_tracking() -> None:
    """
    GET /domains/<domain>/tracking
    :return:
    """
    request = client.domains_tracking.get(domain=domain)
    print(request.json())


def put_open_tracking() -> None:
    """
    PUT /domains/<domain>/tracking/open
    :return:
    """
    data = {"active": "yes", "skip_verification": "false"}
    request = client.domains_tracking_open.put(domain=domain, data=data)
    print(request.json())


def put_click_tracking() -> None:
    """
    PUT /domains/<domain>/tracking/click
    :return:
    """
    data = {
        "active": "yes",
    }
    request = client.domains_tracking_click.put(domain=domain, data=data)
    print(request.json())


def put_unsub_tracking() -> None:
    """
    PUT /domains/<domain>/tracking/unsubscribe
    :return:
    """
    # fmt: off
    data = {
        "active": "yes",
        "html_footer": "\n<br>\n<p><a href=\"%unsubscribe_url%\">UnSuBsCrIbE</a></p>\n",
        "text_footer": "\n\nTo unsubscribe here click: <%unsubscribe_url%>\n\n"
    }
    # fmt: on
    request = client.domains_tracking_unsubscribe.put(domain=domain, data=data)
    print(request.json())


def put_dkim_authority() -> None:
    """
    PUT /domains/<domain>/dkim_authority
    :return:
    """
    data = {"self": "false"}
    request = client.domains_dkimauthority.put(domain=domain, data=data)
    print(request.json())


def put_dkim_selector() -> None:
    """
    PUT /domains/<domain>/dkim_selector
    :return:
    """
    data = {"dkim_selector": "s"}
    request = client.domains_dkimselector.put(domain="python.test.domain5", data=data)
    print(request.json())


def put_web_prefix() -> None:
    """
    PUT /domains/<domain>/web_prefix
    :return:
    """
    data = {"web_prefix": "python"}
    request = client.domains_webprefix.put(domain="python.test.domain5", data=data)
    print(request.json())


def get_sending_queues() -> None:
    """
    GET /domains/<domain>/sending_queues
    :return:
    """
    request = client.domains_sendingqueues.get(domain="python.test.domain5")
    print(request)
    print(request.json())


if __name__ == "__main__":
    get_domains()

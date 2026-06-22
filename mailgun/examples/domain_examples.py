"""Examples for managing Mailgun Domains, Connections, Tracking, and DKIM."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from mailgun.client import AsyncClient, Client

ALLOWED_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,255}$")


# ==============================================================================
# Domain Management (Synchronous)
# ==============================================================================


def get_domains_sync(api_key: str) -> None:
    """
    GET /domains
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domainlist.get()
        print("GET Domains:", response.json())


def add_domain_sync(api_key: str, domain_name: str) -> None:
    """
    POST /domains
    :return: None
    """
    data: dict[str, str] = {
        "name": domain_name,
    }

    with Client(auth=("api", api_key)) as client:
        response = client.domains.create(data=data)
        print("POST Domain:", response.json())
        print("Status Code:", response.status_code)


def get_simple_domain_sync(api_key: str, domain_name: str) -> None:
    """
    GET /domains/<domain>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains.get(domain_name=domain_name)
        print("GET Simple Domain:", response.json())


def update_simple_domain_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>
    :return: None
    """
    data: dict[str, str] = {"name": domain_name, "spam_action": "disabled"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains.put(data=data, domain=domain_name)
        print("PUT Simple Domain:", response.json())


def verify_domain_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/verify
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains.put(domain=domain_name, verify=True)
        print("PUT Verify Domain:", response.json())


def delete_domain_sync(api_key: str, domain_name: str) -> None:
    """
    DELETE /domains/<domain>
    :return: None
    """
    # Delete domain
    with Client(auth=("api", api_key)) as client:
        response = client.domains.delete(domain=domain_name)
        print("DELETE Domain:", response.text)
        print("Status Code:", response.status_code)


# ==============================================================================
# Connection Settings (Synchronous)
# ==============================================================================


def get_connections_sync(api_key: str, domain_name: str) -> None:
    """
    GET /domains/<domain>/connection
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_connection.get(domain=domain_name)
        print("GET Connections:", response.json())


def put_connections_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/connection
    :return: None
    """
    data: dict[str, str] = {"require_tls": "true", "skip_verification": "false"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_connection.put(domain=domain_name, data=data)
        print("PUT Connections:", response.json())


# ==============================================================================
# Tracking Settings (Synchronous)
# ==============================================================================


def get_tracking_sync(api_key: str, domain_name: str) -> None:
    """
    GET /domains/<domain>/tracking
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_tracking.get(domain=domain_name)
        print("GET Tracking:", response.json())


def put_open_tracking_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/tracking/open
    :return: None
    """
    data: dict[str, str] = {"active": "yes", "skip_verification": "false"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_tracking_open.put(domain=domain_name, data=data)
        print("PUT Open Tracking:", response.json())


def put_click_tracking_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/tracking/click
    :return: None
    """
    data: dict[str, str] = {"active": "yes"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_tracking_click.put(domain=domain_name, data=data)
        print("PUT Click Tracking:", response.json())


def put_unsub_tracking_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/tracking/unsubscribe
    :return: None
    """
    # fmt: off
    data: dict[str, str] = {
        "active": "yes",
        "html_footer": "\n<br>\n<p><a href=\"%unsubscribe_url%\">UnSuBsCrIbE</a></p>\n",
        "text_footer": "\n\nTo unsubscribe here click: <%unsubscribe_url%>\n\n"
    }
    # fmt: on
    with Client(auth=("api", api_key)) as client:
        response = client.domains_tracking_unsubscribe.put(domain=domain_name, data=data)
        print("PUT Unsub Tracking:", response.json())


# ==============================================================================
# DKIM & Web Prefix (Synchronous)
# ==============================================================================


def put_dkim_authority_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/dkim_authority
    :return: None
    """
    data: dict[str, str] = {"self": "true"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_dkimauthority.put(domain=domain_name, data=data)
        print("PUT DKIM Authority:", response.json())


def put_dkim_selector_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/dkim_selector
    :return: None
    """
    data: dict[str, str] = {"dkim_selector": "s"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_dkimselector.put(domain=domain_name, data=data)
        print("PUT DKIM Selector:", response.json())


def put_web_prefix_sync(api_key: str, domain_name: str) -> None:
    """
    PUT /domains/<domain>/web_prefix
    :return: None
    """
    data: dict[str, str] = {"web_prefix": "python"}
    with Client(auth=("api", api_key)) as client:
        response = client.domains_webprefix.put(domain=domain_name, data=data)
        print("PUT Web Prefix:", response.json())


def get_sending_queues_sync(api_key: str, domain_name: str) -> None:
    """
    GET /domains/<domain>/sending_queues
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.domains_sendingqueues.get(domain=domain_name)
        print("GET Sending Queues:", response.json())
        print("Status Code:", response.status_code)


def get_dkim_keys_sync(api_key: str, domain_name: str) -> None:
    """
    GET /v1/dkim/keys
    :return: None
    """
    data: dict[str, str] = {
        "page": "string",
        "limit": "0",
        "signing_domain": domain_name,
        "selector": "smtp",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.dkim_keys.get(data=data)
        print("GET DKIM Keys:", response.json())


def post_dkim_keys_sync(api_key: str, domain_name: str, secret_key_filename: str) -> None:
    """
    POST /v1/dkim/keys
    :return: None
    """
    # Private key PEM file must be generated in PKCS1 format. You need 'openssl' on your machine
    # example:
    # openssl genrsa -traditional -out .server.key 2048
    if not ALLOWED_FILENAME_RE.match(secret_key_filename):
        raise ValueError(f"Invalid filename: {secret_key_filename!r}")

    secret_key_path = Path(secret_key_filename)
    subprocess.run(
        ["openssl", "genrsa", "-traditional", "-out", secret_key_filename, "--", "2048"], check=True
    )

    files = [
        (
            "pem",
            ("server.key", secret_key_path.read_bytes()),
        )
    ]

    data: dict[str, Any] = {
        "signing_domain": domain_name,
        "selector": "smtp",
        "bits": "2048",
    }

    # Note: Explicitly providing {"Content-Type": "multipart/form-data"} here breaks `requests`
    # and `httpx` because they auto-generate the necessary multipart boundary string.
    with Client(auth=("api", api_key)) as client:
        response = client.dkim_keys.create(data=data, files=files)
        print("POST DKIM Keys:", response.json())

    # Safely clean up the generated key
    if secret_key_path.exists():
        secret_key_path.unlink()


def delete_dkim_keys_sync(api_key: str, domain_name: str) -> None:
    """
    DELETE /v1/dkim/keys
    :return: None
    """
    query: dict[str, str] = {"signing_domain": domain_name, "selector": "smtp"}
    with Client(auth=("api", api_key)) as client:
        response = client.dkim_keys.delete(filters=query)
        print("DELETE DKIM Keys:", response.json())


# ==============================================================================
# Domain Management (Asynchronous Example)
# ==============================================================================


async def get_domains_async(api_key: str) -> None:
    """
    GET /domains (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.domainlist.get()
        print("GET Domains (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")
    TARGET_DOMAIN: str = "python.test.com"
    SECRET_KEY_FILE: str = os.environ.get("SECRET_KEY_FILENAME", "server.key")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        # Domain Management
        add_domain_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        get_domains_sync(api_key=API_KEY)
        get_simple_domain_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        update_simple_domain_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        verify_domain_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        delete_domain_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)

        # Connection Settings
        get_connections_sync(api_key=API_KEY, domain_name=DOMAIN)
        put_connections_sync(api_key=API_KEY, domain_name=DOMAIN)

        # Tracking Settings
        get_tracking_sync(api_key=API_KEY, domain_name=DOMAIN)
        put_open_tracking_sync(api_key=API_KEY, domain_name=DOMAIN)
        put_click_tracking_sync(api_key=API_KEY, domain_name=DOMAIN)
        put_unsub_tracking_sync(api_key=API_KEY, domain_name=DOMAIN)

        # DKIM & Web Prefix
        put_dkim_authority_sync(api_key=API_KEY, domain_name=DOMAIN)
        put_dkim_selector_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        put_web_prefix_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)

        # Sending Queues
        get_sending_queues_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)

        # DKIM Keys Lifecycle
        post_dkim_keys_sync(
            api_key=API_KEY, domain_name=TARGET_DOMAIN, secret_key_filename=SECRET_KEY_FILE
        )
        get_dkim_keys_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)
        delete_dkim_keys_sync(api_key=API_KEY, domain_name=TARGET_DOMAIN)

        # Run Async Example
        asyncio.run(get_domains_async(api_key=API_KEY))

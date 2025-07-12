"""DOMAINS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-domains.html#
"""

from __future__ import annotations

from os import path
from typing import Any
from urllib.parse import urljoin

from .error_handler import ApiError


def handle_domainlist(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **_: Any,
) -> Any:
    """Handle a list of domains.

    :param url: Incoming URL dictionary
    :type url: dict
    :param _domain: Incoming domain (it's not being used for this handler)
    :type _domain: str
    :param _method: Incoming request method (it's not being used for this handler)
    :type _method: str
    :param _: kwargs
    :return: final url for domainlist endpoint
    """
    return url["base"] + "domains"


def handle_domains(
    url: Any,
    domain: str | None,
    method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle a domain endpoint.

    :param url: Incoming URL dictionary
    :type url: dict
    :param domain: Incoming domain
    :type domain: str
    :param method: Incoming request method
    :type method: str
    :param kwargs: kwargs
    :return: final url for domain endpoint
    :raises: ApiError
    """
    # TODO: Refactor this logic
    # fmt: off
    if "domains" in url["keys"]:
        domains_index = url["keys"].index("domains")
        url["keys"].pop(domains_index)
    if url["keys"]:
        final_keys = path.join("/", *url["keys"]) if url["keys"] else ""
        if not domain:
            raise ApiError("Domain is missing!")
        if "login" in kwargs:
            url = urljoin(url["base"], domain + final_keys + "/" + kwargs["login"])
        elif "ip" in kwargs:
            url = urljoin(url["base"], domain + final_keys + "/" + kwargs["ip"])
        elif "unlink_pool" in kwargs:
            url = urljoin(url["base"], domain + final_keys + "/ip_pool")
        elif "api_storage_url" in kwargs:
            url = kwargs["api_storage_url"]
        else:
            url = urljoin(url["base"], domain + final_keys)
    elif method in {"get", "post", "delete"}:
        if "domain_name" in kwargs:
            url = urljoin(url["base"], kwargs["domain_name"])
        elif method == "delete":
            # TODO: Remove replacing v4 with v3 when the 'Delete a domain API' will be updated to v4, see https://documentation.mailgun.com/docs/mailgun/api-reference/openapi-final/tag/Domains/#tag/Domains/operation/DELETE-v3-domains--name-
            url = urljoin(url["base"].replace("/v4/", "/v3/"), domain)

        else:
            url = url["base"][:-1]
    elif "verify" in kwargs:
        if kwargs["verify"] is not True:
            raise ApiError("Verify option should be True or absent")
        url = url["base"] + domain + "/verify"
    else:
        url = urljoin(url["base"], domain)
    # fmt: on
    return url


def handle_sending_queues(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str | Any:
    """Handle sending queues endpoint URL construction."""
    return url["base"][:-1] + f"/{domain}/sending_queues"

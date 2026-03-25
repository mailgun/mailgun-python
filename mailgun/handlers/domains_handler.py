"""DOMAINS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-domains.html#
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from .error_handler import ApiError


def handle_domainlist(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **_: Any,
) -> Any:
    """Handle a list of domains."""
    # Ensure base ends with slash before appending
    return url["base"].rstrip("/") + "/domains"


def handle_domains(
    url: Any,
    domain: str | None,
    method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle a domain endpoint."""
    if "domains" in url["keys"]:
        domains_index = url["keys"].index("domains")
        url["keys"].pop(domains_index)

    base_url = url["base"]

    if url["keys"]:
        # Safe concatenation without leading slash to avoid //
        final_keys = "/".join(url["keys"])
        if not domain:
            raise ApiError("Domain is missing!")

        # Ensure base URL ends with slash
        if not base_url.endswith("/"):
            base_url += "/"

        # Construct path: base_url + domain + / + final_keys
        domain_path = f"{domain}/{final_keys}"

        if "login" in kwargs:
            return f"{base_url}{domain_path}/{kwargs['login']}"
        if "ip" in kwargs:
            return f"{base_url}{domain_path}/{kwargs['ip']}"
        if "unlink_pool" in kwargs:
            return f"{base_url}{domain_path}/ip_pool"
        if "api_storage_url" in kwargs:
            return kwargs["api_storage_url"]
        return f"{base_url}{domain_path}"

    if method in {"get", "post", "delete"}:
        if "domain_name" in kwargs:
            # e.g. /v4/domains/domain_name
            return urljoin(base_url, kwargs["domain_name"])
        if method == "delete":
            # Parity with legacy API where delete stays on V3
            # url["base"] is e.g. https://api.mailgun.net/v4/domains/
            v3_base = base_url.replace("/v4/", "/v3/")
            return urljoin(v3_base, domain) if domain else v3_base
        # e.g. POST /domains
        return base_url.removesuffix("/")

    if "verify" in kwargs:
        if kwargs["verify"] is not True:
            raise ApiError("Verify option should be True or absent")
        # Ensure base ends with slash
        base = base_url if base_url.endswith("/") else f"{base_url}/"
        return f"{base}{domain}/verify"
    return urljoin(base_url, domain) if domain else base_url


def handle_sending_queues(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str | Any:
    """Handle sending queues endpoint URL construction."""
    if "sending_queues" in url["keys"] or "sendingqueues" in url["keys"]:
        # Base is typically .../v3/domains/. We need .../v3/{domain}/sending_queues
        # So we strip 'domains/' or just use replace.
        base_clean = url["base"].replace("domains/", "").replace("domains", "")
        if not base_clean.endswith("/"):
            base_clean += "/"
        return f"{base_clean}{domain}/sending_queues"
    return None


def handle_mailboxes_credentials(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle Mailboxes credentials."""
    final_keys = "/".join(url["keys"]) if url["keys"] else ""
    base_url = url["base"] if url["base"].endswith("/") else f"{url['base']}/"

    constructed_url = f"{base_url}{domain}/{final_keys}" if final_keys else f"{base_url}{domain}"

    if "login" in kwargs:
        return f"{constructed_url}/{kwargs['login']}"
    return constructed_url


def handle_dkimkeys(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> Any:
    """Handle DKIM Keys."""
    # url["keys"] usually contains ['dkim', 'keys'] from our manifest
    final_keys = "/".join(url["keys"]) if url["keys"] else ""

    base_url = url["base"]
    if not base_url.endswith("/"):
        base_url += "/"

    # The result should be exactly https://api.mailgun.net/v1/dkim/keys
    return base_url + final_keys

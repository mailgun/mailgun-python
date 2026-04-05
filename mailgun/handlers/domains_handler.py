"""DOMAINS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-domains.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys


def handle_domainlist(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **_: Any,
) -> str:
    """Handle a list of domains.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **_: Additional keyword arguments (unused).

    Returns:
        The final URL for the domainlist endpoint.
    """
    # Ensure base ends with slash before appending
    return url["base"].rstrip("/") + "/domains"


def handle_domains(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle a domain endpoint URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method.
        **kwargs: Additional keyword arguments (e.g., 'domain_name', 'verify').

    Returns:
        The final URL for the domain endpoint.

    Raises:
        ApiError: If the domain is missing.
    """
    keys = list(url["keys"])
    if "domains" in keys:
        keys.remove("domains")

    base_url = str(url["base"]).rstrip("/")
    target_domain = kwargs.get("domain_name", domain)

    if not target_domain:
        if keys:
            raise ApiError("Domain is missing!")
        return base_url

    # Hierarchical construction: [domain] + [remaining keys from Config]
    path_segments = [target_domain, *keys]
    domain_path = "/".join(path_segments)

    # Specific terminal logic for special arguments
    if "login" in kwargs:
        return f"{base_url}/{domain_path}/{kwargs['login']}"

    if "ip" in kwargs:
        # Check if 'ips' segment is already present to prevent domains/ips/ips/1.1.1.1
        prefix = "" if "ips" in keys else "ips/"
        return f"{base_url}/{domain_path}/{prefix}{kwargs['ip']}"

    if "verify" in kwargs:
        if kwargs["verify"]:
            # Append /verify only if it wasn't already in the keys list
            return (
                f"{base_url}/{domain_path}"
                if "verify" in keys
                else f"{base_url}/{domain_path}/verify"
            )
        raise ApiError("Verify option should be True")

    return f"{base_url}/{domain_path}"


def handle_sending_queues(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **_kwargs: Any,
) -> str:
    """Handle sending queues URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'domain_name').

    Returns:
        The final URL for the sending queues endpoint.
    """
    keys = url["keys"]
    if "sending_queues" in keys or "sendingqueues" in keys:
        base_clean = str(url["base"]).replace("domains/", "").replace("domains", "").rstrip("/")
        return f"{base_clean}/{domain}/sending_queues"
    return str(url["base"])


def handle_mailboxes_credentials(
    url: dict[str, Any],
    domain: str | None,
    _method: str | None,
    **kwargs: Any,
) -> str:
    """Handle Mailboxes credentials URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name.
        _method: Incoming request method (unused in this handler).
        **kwargs: Additional keyword arguments (e.g., 'domain_name', 'login').

    Returns:
        The final URL for the Mailboxes credentials endpoint.

    Raises:
        ApiError: If the domain is missing.
    """
    keys = list(url["keys"])
    if "domains" in keys:
        keys.remove("domains")

    base_url = str(url["base"]).rstrip("/")
    target_domain = kwargs.get("domain_name", domain)

    if not target_domain:
        raise ApiError("Domain is missing!")

    path_segments = [target_domain, *keys]
    constructed_url = f"{base_url}/{'/'.join(path_segments)}"

    if "login" in kwargs:
        return f"{constructed_url}/{kwargs['login']}"
    return constructed_url


def handle_dkimkeys(
    url: dict[str, Any],
    _domain: str | None,
    _method: str | None,
    **_kwargs: Any,
) -> str:
    """Handle DKIM keys URL construction.

    Args:
        url: Incoming URL configuration dictionary.
        _domain: Incoming domain (unused in this handler).
        _method: Incoming request method (unused in this handler).
        **_kwargs: Additional keyword arguments (unused).

    Returns:
        The final URL for the DKIM keys endpoint.
    """
    final_keys = build_path_from_keys(url.get("keys", []))
    base_url = str(url["base"]).rstrip("/")
    return f"{base_url}{final_keys}"

"""DOMAINS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-domains.html
"""

from __future__ import annotations

from typing import Any

from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.utils import build_path_from_keys, sanitize_path_segment


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

    # 1. Sanitize the target domain, especially since it can be overridden by kwargs
    raw_target_domain = kwargs.get("domain_name", domain)
    target_domain = sanitize_path_segment(raw_target_domain) if raw_target_domain else None

    if not target_domain:
        if keys:
            raise ApiError("Domain is missing!")
        return base_url

    # Hierarchical construction: [domain] + [remaining keys from Config]
    path_segments = [target_domain, *keys]
    domain_path = build_path_from_keys(path_segments).lstrip(
        "/"
    )  # Strip the leading slash to match the original behavior

    # 2. Sanitize mailbox logins (which often contain special characters like '@' or '.')
    if "login" in kwargs:
        safe_login = sanitize_path_segment(kwargs["login"])
        return f"{base_url}/{domain_path}/{safe_login}"

    # 3. Sanitize IP addresses
    if "ip" in kwargs:
        # Check if 'ips' segment is already present to prevent domains/ips/ips/1.1.1.1
        prefix = "" if "ips" in keys else "ips/"
        safe_ip = sanitize_path_segment(kwargs["ip"])
        return f"{base_url}/{domain_path}/{prefix}{safe_ip}"

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
        safe_login = sanitize_path_segment(kwargs["login"])
        return f"{base_url}/{target_domain}/credentials/{safe_login}"
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


def handle_webhooks(
    url: dict[str, Any],
    domain: str | None,
    method: str | None,
    **kwargs: Any,
) -> str:
    """Dynamically route webhooks to v1, v3, or v4 based on domain and payload.

    Args:
        url: The base URL and keys dictionary.
        domain: Target domain name.
        method: Requested HTTP method (e.g., 'post', 'put', 'delete', 'get').
        **kwargs: Additional parameters including 'webhook_name', 'webhook_id', 'data', and 'filters'.

    Returns:
        The formulated webhook URL string.
    """
    base_url = str(url["base"]).rstrip("/")
    keys = list(url.get("keys", []))

    # 1. Account Webhooks (v1)
    if "/v1" in base_url or not domain:
        final_keys = build_path_from_keys(keys)
        path = f"{base_url}{final_keys}"
        if "webhook_id" in kwargs:
            safe_id = sanitize_path_segment(kwargs["webhook_id"])
            return f"{path}/{safe_id}"
        return path

    # 2. Domain Webhooks (v3 or v4)
    webhook_name = kwargs.get("webhook_name")

    # Fluent API support (e.g., client.domains_webhooks_clicked -> keys=["webhooks", "clicked"])
    if len(keys) > 1 and keys[0] == "webhooks":
        webhook_name = webhook_name or keys[1]
        keys = [keys[0]]

    data = kwargs.get("data") or {}
    filters = kwargs.get("filters") or {}

    # Payload Detection (Content-Based Routing)
    has_event_types = isinstance(data, dict) and "event_types" in data
    has_url_query = isinstance(filters, dict) and "url" in filters
    method_lower = (method or "").lower()

    is_v4 = False
    if (method_lower in {"post", "put"} and has_event_types) or (
        method_lower == "delete" and has_url_query
    ):
        is_v4 = True

    if is_v4:
        # Dynamic upgrade: Replace version without hardcoding the host
        base_url = base_url.replace("/v3/", "/v4/")

    final_keys_str = build_path_from_keys(keys)
    domain_path = f"{base_url}/{domain}{final_keys_str}"

    if not is_v4 and webhook_name:
        # v3 API requires webhook name in the URL
        return f"{domain_path}/{webhook_name}"

    return domain_path

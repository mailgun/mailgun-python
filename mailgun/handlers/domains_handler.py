"""DOMAINS HANDLER.

Doc: https://documentation.mailgun.com/en/latest/api-domains.html
"""

from __future__ import annotations

from typing import Any

from mailgun.endpoints import build_path_from_keys
from mailgun.handlers.error_handler import ApiError
from mailgun.security import SecurityGuard


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
    return str(url.get("base", "")).rstrip("/") + "/domains"


def handle_domains(  # noqa: PLR0914
    url: dict[str, Any],
    domain: str | None = None,
    _method: str | None = None,
    data: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    **kwargs: Any,
) -> str:
    """Handle a domain endpoint URL construction.

    Dynamically maps routing for domains, credentials, tracking, and webhooks
    while preserving V4 upgrade paths and mitigating path traversal.

    Args:
        url: Incoming URL configuration dictionary.
        domain: Target domain name, if applicable.
        _method: HTTP request method.
        data: Optional request payload dictionary.
        filters: Optional query filters dictionary.
        **kwargs: Additional routing arguments (e.g., login, webhook_name, ip, verify).

    Returns:
        The constructed and sanitized target URL string.

    Raises:
        ApiError: If the domain is missing or options are invalid.
    """
    keys = list(url.get("keys", []))
    if "domains" in keys:
        keys.remove("domains")

    base_url = str(url.get("base", "")).rstrip("/")

    # --- 1. Identify Target Domain ---
    raw_target_domain = kwargs.get("domain_name", domain)
    target_domain = (
        SecurityGuard.sanitize_path_segment(raw_target_domain) if raw_target_domain else None
    )

    # --- 2. Dynamic V4 Upgrade for Webhooks ---
    webhook_name = kwargs.get("webhook_name")
    if len(keys) > 1 and keys[0] == "webhooks":
        webhook_name = webhook_name or keys[1]
        keys = [keys[0]]

    data_dict = data or kwargs.get("data", {})
    filters_dict = filters or kwargs.get("filters", {})
    method_lower = (_method or "").lower()

    has_event_types = isinstance(data_dict, dict) and "event_types" in data_dict
    has_url_query = isinstance(filters_dict, dict) and "url" in filters_dict

    if "webhooks" in keys and (
        (method_lower in {"post", "put"} and has_event_types)
        or (method_lower == "delete" and has_url_query)
    ):
        base_url = base_url.replace("/v3/", "/v4/")

    if not target_domain:
        if keys:
            raise ApiError("Domain is missing!")
        return base_url

    # --- 3. Build Base Domain Path ---
    path_segments = [target_domain, *keys]
    domain_path = build_path_from_keys(path_segments).lstrip("/")
    final_url = f"{base_url}/{domain_path}"

    # --- 4. Append Dynamic Sub-Resources ---

    # A. Webhook Names
    if "webhooks" in keys and webhook_name:
        safe_webhook = SecurityGuard.sanitize_path_segment(webhook_name)
        return f"{final_url}/{safe_webhook}"

    # B. Credentials Logins (CRITICAL FIX: Correct path segment handling)
    login_val = kwargs.pop("login", None)
    if "credentials" in keys and login_val is not None:
        login_str = str(login_val)

        # If the login includes the domain, strip the extra domain part if it duplicates the target domain
        if "@" in login_str:
            local_part, domain_part = login_str.split("@", 1)
            if domain and domain_part == domain:
                safe_login = SecurityGuard.sanitize_path_segment(local_part)
            else:
                safe_login = f"{SecurityGuard.sanitize_path_segment(local_part)}@{SecurityGuard.sanitize_path_segment(domain_part)}"
        else:
            safe_login = SecurityGuard.sanitize_path_segment(login_str)

        return f"{final_url}/{safe_login}"

    # C. IP Addresses
    if "ip" in kwargs:
        prefix = "" if "ips" in keys else "ips/"
        safe_ip = SecurityGuard.sanitize_path_segment(kwargs.pop("ip"))
        return f"{final_url}/{prefix}{safe_ip}"

    # D. Verify Flag
    if "verify" in kwargs:
        verify_val = kwargs.pop("verify")
        if verify_val:
            return final_url if "verify" in keys else f"{final_url}/verify"
        raise ApiError("Verify option should be True")

    return final_url


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
        **_kwargs: Additional keyword arguments (e.g., 'domain_name').

    Returns:
        The final URL for the sending queues endpoint.
    """
    keys = url.get("keys", [])
    if "sending_queues" in keys or "sendingqueues" in keys:
        # Safely strip the trailing suffix without mangling custom proxy hosts
        base_clean = str(url["base"]).rstrip("/")
        if base_clean.endswith("/domains"):
            base_clean = base_clean.removesuffix("/domains")

        safe_domain = SecurityGuard.sanitize_path_segment(domain) if domain else ""
        return f"{base_clean}/{safe_domain}/sending_queues"

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
    keys = list(url.get("keys", []))

    if "domains" in keys:
        keys.remove("domains")

    base_url = str(url["base"]).rstrip("/")

    # Sanitize the target domain
    raw_target_domain = kwargs.get("domain_name", domain)
    target_domain = (
        SecurityGuard.sanitize_path_segment(raw_target_domain) if raw_target_domain else None
    )

    if not target_domain:
        if keys:
            raise ApiError("Domain is missing!")
        return base_url

    path_segments = [target_domain, *keys]
    constructed_url = f"{base_url}/{'/'.join(path_segments)}"

    if "login" in kwargs:
        safe_login = SecurityGuard.sanitize_path_segment(kwargs["login"])
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


def handle_webhooks(  # noqa: PLR0914
    url: dict[str, Any],
    domain: str | None,
    method: str | None,
    data: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
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
            safe_id = SecurityGuard.sanitize_path_segment(kwargs["webhook_id"])
            return f"{path}/{safe_id}"
        return path

    # 2. Domain Webhooks (v3 or v4)
    webhook_name = kwargs.get("webhook_name")

    # Fluent API support (e.g., client.domains_webhooks_clicked -> keys=["webhooks", "clicked"])
    if len(keys) > 1 and keys[0] == "webhooks":
        webhook_name = webhook_name or keys[1]
        keys = [keys[0]]

    data_dict = data or {}
    filters_dict = filters or {}

    # Payload Detection (Content-Based Routing)
    has_event_types = isinstance(data_dict, dict) and "event_types" in data_dict
    has_url_query = isinstance(filters_dict, dict) and "url" in filters_dict
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

    # CWE-20/22: Sanitize domain boundary
    safe_domain = SecurityGuard.sanitize_path_segment(domain) if domain else ""
    domain_path = f"{base_url}/{safe_domain}{final_keys_str}"

    if not is_v4 and webhook_name:
        # v3 API requires webhook name in the URL
        safe_webhook_name = SecurityGuard.sanitize_path_segment(webhook_name)
        return f"{domain_path}/{safe_webhook_name}"

    return domain_path

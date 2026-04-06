"""Mailgun API Routes Configuration."""

from __future__ import annotations


# EXACT_ROUTES map an attribute to an exact API version and path array.
EXACT_ROUTES: dict[str, list[str | list[str]]] = {
    "messages": ["v3", ["messages"]],
    "mimemessage": ["v3", ["messages.mime"]],
    "resend_message": ["v3", ["resendmessage"]],
    "ippools": ["v3", ["ip_pools"]],
    "dkim_keys": ["v1", ["dkim", "keys"]],
    "dkim": ["v1", ["dkim", "keys"]],
    "domainlist": ["v4", ["domainlist"]],
    "analytics": ["v1", ["analytics", "usage", "metrics", "logs", "tags", "limits"]],
    "bounce_classification": ["v2", ["bounce-classification", "metrics"]],
    "users": ["v5", ["users", "me"]],
    "subaccount_ip_pools": ["v5", ["accounts", "subaccounts", "ip_pools"]],
    "subaccount_ip_pool": ["v5", ["accounts", "subaccounts", "{subaccountId}", "ip_pool"]],
    "dkim_management_rotation": ["v1", ["dkim_management", "domains", "{name}", "rotation"]],
    "dkim_management_rotate": ["v1", ["dkim_management", "domains", "{name}", "rotate"]],
    "account_templates": ["v4", ["templates"]],
    "account_webhooks": ["v1", ["webhooks"]],
    "x509": ["v2", ["x509", "{domain}"]],
    "x509_status": ["v2", ["x509", "{domain}", "status"]],
}

# PREFIX_ROUTES map attributes to a base version, path prefix, and optional suffix.
PREFIX_ROUTES: dict[str, list[str | None]] = {
    "templates": ["v3", "", None],
    "analytics": ["v1", "", None],
    "bounceclassification": ["v2", "", "bounce-classification"],
    "credentials": ["v3", "domains", None],
    "domains": ["v3", "domains", None],
    "webhooks": ["v3", "domains", None],
    "spamtraps": ["v3", "", None],
    "blocklists": ["v3", "", None],
    "reputation": ["v3", "", None],
    "users": ["v5", "", None],
    "keys": ["v1", "", None],
    "thresholds": ["v1", "", None],
    "events": ["v3", "", None],
    "tags": ["v3", "", None],
    "bounces": ["v3", "", None],
    "unsubscribes": ["v3", "", None],
    "complaints": ["v3", "", None],
    "whitelists": ["v3", "", None],
    "routes": ["v3", "", None],
    "lists": ["v3", "", None],
    "mailboxes": ["v3", "", None],
    "stats": ["v3", "", None],
    "ips": ["v3", "", None],
    "ip_pools": ["v3", "", None],
    "ip_whitelist": ["v3", "ip", "whitelist"],
    # Validations Service API
    "addressparse": ["v4", "address/parse", "addressparse"],
    "addressvalidate": ["v4", "address", "validate"],
    "address": ["v4", "", None],
    # Email Preview & Code Analysis API
    "inspect": ["v1", "", None],
    "preview": ["v1", "", None],
    "preview_v2": ["v2", "preview", None],
    # Mailgun Optimize API
    "alerts": ["v1", "", None],
    "inboxready": ["v1", "", None],
    "dmarc": ["v1", "", None],
    "reputationanalytics": ["v1", "", None],
    # Account Level
    "accounts": ["v5", "", None],
    "sandbox": ["v5", "", None],
}

DOMAIN_ALIASES: dict[str, str] = {
    "dkimauthority": "dkim_authority",
    "dkimselector": "dkim_selector",
    "webprefix": "web_prefix",
    "sendingqueues": "sending_queues",
}

DOMAIN_ENDPOINTS: dict[str, list[str]] = {
    "v1": ["click", "open", "unsubscribe", "dkim", "webhooks", "security"],
    "v4": ["ips", "connections"],
    "v3": [
        "credentials",
        "verify",
        "messages",
        "tags",
        "bounces",
        "unsubscribes",
        "complaints",
        "whitelists",
        "stats",
        "events",
        "routes",
        "lists",
        "mailboxes",
        "ip_pools",
        "sending_queues",
        "tracking",  # 'tracking' natively lives here
    ],
}

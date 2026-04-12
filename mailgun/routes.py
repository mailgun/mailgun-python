"""Mailgun API Routes Configuration."""

from __future__ import annotations

import re


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
    "account_templates": ["v4", ["templates"]],
    "account_webhooks": ["v1", ["webhooks"]],
    # Validation Service
    "addressvalidate": ["v4", ["address", "validate"]],
    "addressparse": ["v4", ["address", "parse"]],
    "address": ["v4", ["address", "validate", "bulk"]],
    # Mailgun Optimize & Previews
    "inspect": ["v1", ["inspect", "analyze"]],
    "preview": ["v1", ["preview", "tests"]],
    "preview_v2": ["v2", ["preview", "tests"]],
    "alerts": ["v1", ["alerts", "events"]],
    "dmarc": ["v1", ["dmarc", "records", "{domain}"]],
    "inboxready": ["v1", ["inboxready", "domains"]],
    "reputationanalytics": ["v1", ["reputationanalytics", "snds"]],
    # Standard Domain Endpoints (Merged paths to avoid handle_domains intercept)
    "spamtraps": ["v3", ["domains/{domain}/spamtraps"]],
    "blocklists": ["v3", ["domains/{domain}/blocklists"]],
    # MTLS and DKIM
    "x509": ["v2", ["x509", "{domain}"]],
    "x509_status": ["v2", ["x509", "{domain}", "status"]],
    "dkim_management_rotation": ["v1", ["dkim_management", "domains", "{domain}", "rotation"]],
    "dkim_management_rotate": ["v1", ["dkim_management", "domains", "{domain}", "rotate"]],
    # Subaccounts (FIXED: Added placeholders to match Mailgun V5 requirements)
    "accounts": ["v5", ["accounts", "subaccounts"]],
    "subaccount_ip_pools": ["v5", ["accounts", "subaccounts", "{subaccountId}", "ip_pools"]],
    "subaccount_ip_pool": ["v5", ["accounts", "subaccounts", "{subaccountId}", "ip_pool"]],
}

# PREFIX_ROUTES map attributes to a base version, path prefix, and optional suffix.
PREFIX_ROUTES: dict[str, list[str | None]] = {
    "templates": ["v3", "", None],
    "analytics": ["v1", "", None],
    "bounceclassification": ["v2", "", "bounce-classification"],
    "credentials": ["v3", "domains", None],
    "domains": ["v3", "domains", None],
    "webhooks": ["v3", "domains", None],
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
    "sandbox": ["v5", "", None],
}

DOMAIN_ALIASES: dict[str, str] = {
    "dkimauthority": "dkim_authority",
    "dkimselector": "dkim_selector",
    "webprefix": "web_prefix",
    "sendingqueues": "sending_queues",
}

DOMAIN_ENDPOINTS: dict[str, list[str]] = {
    "v1": ["dkim", "security"],
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
        "tracking",
        "click",
        "open",
        "unsubscribe",
        "webhooks",
    ],
}

DEPRECATED_ROUTES: dict[re.Pattern[str], str] = {
    re.compile(
        r"^/v1/bounce-classification/"
    ): "The v1 bounce-classification API is deprecated. Migrate to POST /v2/bounce-classification/metrics.",
    re.compile(
        r"^/v3/(stats|[^/]+/stats|[^/]+/aggregates)"
    ): "The v3 Stats API is deprecated. Migrate to the v1 Metrics API.",
    re.compile(
        r"^/v3/[^/]+/tag(/|$|\?)"
    ): "The legacy Tag API is deprecated. Migrate to the new Tags API (/v3/{domain}/tags).",
    re.compile(r"^/v3/domains/[^/]+/limits/tag"): "The domain tag limits API is deprecated.",
    re.compile(
        r"^/v3/lists/[^/]+/validate"
    ): "The v3 Bulk Validation API is deprecated. Migrate to the v4 Bulk Validations Service.",
    re.compile(
        r"^/v3/address/(validate|parse|private)"
    ): "The v3 Address Validation/Parsing APIs are deprecated. Migrate to the v4 Validations Service.",
}

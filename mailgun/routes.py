"""Mailgun API Routes Configuration.

This module defines the map of routes, prefixes, and deprecated API paths.
All public dictionaries are immutable (read-only) to prevent accidental
configuration changes during SDK runtime.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Final


# Simplified, scalable, and valid type aliases
ExactRouteType = dict[str, tuple[str, tuple[str, ...]]]
PrefixRoutesType = dict[str, tuple[str, str, str | None]]
DomainsAliasType = dict[str, str]
DomainsEndpointsType = dict[str, tuple[str, ...]]
DeprecatedRoutesType = dict[re.Pattern[str], str]


# --- EXACT_ROUTES ---
# Mapping of attributes to an exact API version and path array.
_EXACT_ROUTES: ExactRouteType = {
    "messages": ("v3", ("messages",)),
    "mimemessage": ("v3", ("messages.mime",)),
    "resend_message": ("v3", ("resendmessage",)),
    "ippools": ("v3", ("ip_pools",)),
    "dkim_keys": ("v1", ("dkim", "keys")),
    "dkim": ("v1", ("dkim", "keys")),
    "domainlist": ("v4", ("domainlist",)),
    "bounce_classification": ("v2", ("bounce-classification", "metrics")),
    "users": ("v5", ("users", "me")),
    # Account level definitions
    "account_templates": ("v4", ("templates",)),
    "account_webhooks": ("v1", ("webhooks",)),
    # Validation Service
    "addressvalidate": ("v4", ("address", "validate")),
    "addressparse": ("v4", ("address", "parse")),
    "address_bulk": ("v4", ("address", "validate", "bulk")),
    # Standard Domain Endpoints (Merged paths to avoid handle_domains intercept)
    "spamtraps": ("v2", ("spamtraps",)),
    "blocklists": ("v3", ("domains", "{domain}", "blocklists")),
    # MTLS and DKIM Management
    "x509": ("v2", ("x509", "{domain}")),
    "x509_status": ("v2", ("x509", "{domain}", "status")),
    "dkim_management_rotation": ("v1", ("dkim_management", "domains", "{domain}", "rotation")),
    "dkim_management_rotate": ("v1", ("dkim_management", "domains", "{domain}", "rotate")),
    # Subaccounts
    "subaccount_ip_pools": ("v5", ("accounts", "subaccounts", "{subaccountId}", "ip_pools")),
    "subaccount_ip_pool": ("v5", ("accounts", "subaccounts", "{subaccountId}", "ip_pool")),
}

EXACT_ROUTES: Final = MappingProxyType(_EXACT_ROUTES)


# --- PREFIX_ROUTES ---
# Defines the base version, path suffix, and an optional key override for handlers.
# Corrected to eliminate suffix duplication and allow clean string joining.
_PREFIX_ROUTES: PrefixRoutesType = {
    # Send & Core Services
    "templates": ("v3", "", None),
    "credentials": ("v3", "domains", None),
    "domains": ("v3", "domains", None),
    "webhooks": ("v3", "domains", None),
    "events": ("v3", "", None),
    "tags": ("v3", "", None),
    "bounces": ("v3", "", None),
    "unsubscribes": ("v3", "", None),
    "complaints": ("v3", "", None),
    "whitelists": ("v3", "", None),
    "routes": ("v3", "", None),
    "lists": ("v3", "", None),
    "mailboxes": ("v3", "", None),
    "stats": ("v3", "", None),
    "ips": ("v3", "", None),
    "ip_pools": ("v3", "", None),
    "ip_warmups": ("v3", "", None),
    "ip_whitelist": ("v2", "ip", "whitelist"),
    "envelopes": ("v3", "", None),
    # Subaccounts & Limits
    "accounts": ("v5", "", None),
    "sandbox": ("v5", "", None),
    "users": ("v5", "", None),
    # Analytics, Metrics, & Logs
    "analytics": ("v1", "", None),
    "bounceclassification": ("v2", "", "bounce-classification"),
    "reputation": ("v3", "", None),
    # Alerts & Thresholds
    "alerts": ("v1", "", None),
    "thresholds": ("v1", "", None),
    # Keys & Security
    "keys": ("v1", "", None),
    # Validation Service
    "address": ("v4", "", None),
    # InboxReady & Optimize
    "inbox": ("v4", "", None),
    "inboxready": ("v1", "", None),
    "inspect": ("v1", "", None),
    "preview": ("v1", "", None),
    "preview_v2": ("v2", "", "preview"),
    "dmarc": ("v1", "", None),
    "monitoring": ("v1", "", None),
    "reputationanalytics": ("v1", "", None),
    "maverick_score": ("v1", "", "maverick-score"),
}

PREFIX_ROUTES: Final = MappingProxyType(_PREFIX_ROUTES)


# --- DOMAIN_ALIASES ---
# Mapping of shortened or logical names to physical path segments.
_DOMAIN_ALIASES: DomainsAliasType = {
    "dkimauthority": "dkim_authority",
    "dkimselector": "dkim_selector",
    "webprefix": "web_prefix",
    "sendingqueues": "sending_queues",
}

DOMAIN_ALIASES: Final = MappingProxyType(_DOMAIN_ALIASES)


# --- DOMAIN_ENDPOINTS ---
# Grouping endpoints by versions for smart routing.
_DOMAIN_ENDPOINTS: DomainsEndpointsType = {
    "v1": ("dkim", "security"),
    "v4": ("ips", "connections"),
    "v3": (
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
    ),
}

DOMAIN_ENDPOINTS: Final = MappingProxyType(_DOMAIN_ENDPOINTS)


# --- DEPRECATED_ROUTES ---
# Regular expressions to identify deprecated paths and their corresponding messages.
_DEPRECATED_ROUTES: DeprecatedRoutesType = {
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

DEPRECATED_ROUTES: Final = MappingProxyType(_DEPRECATED_ROUTES)

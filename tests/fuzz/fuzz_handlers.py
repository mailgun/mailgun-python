#!/usr/bin/env python3
"""Fuzz test for Mailgun API Route Handlers.

Focus: Deep Path Traversal, Template Injection, Sub-resource Transitions,
Parameter Type Confusion, and URL Interpolation Resiliency.
"""

import atexit
import logging
import sys
from collections.abc import Callable
from typing import Any

import atheris

with atheris.instrument_imports():
    from mailgun.handlers.bounce_classification_handler import (
        handle_bounce_classification,
    )
    from mailgun.handlers.default_handler import handle_default
    from mailgun.handlers.domains_handler import handle_domainlist, handle_domains
    from mailgun.handlers.email_validation_handler import handle_address_validate
    from mailgun.handlers.error_handler import ApiError
    from mailgun.handlers.inbox_placement_handler import handle_inbox
    from mailgun.handlers.ip_pools_handler import handle_ippools
    from mailgun.handlers.ips_handler import handle_ips
    from mailgun.handlers.keys_handler import handle_keys
    from mailgun.handlers.mailinglists_handler import handle_lists
    from mailgun.handlers.messages_handler import handle_resend_message
    from mailgun.handlers.metrics_handler import handle_metrics
    from mailgun.handlers.routes_handler import handle_routes
    from mailgun.handlers.suppressions_handler import (
        handle_bounces,
        handle_complaints,
        handle_unsubscribes,
        handle_whitelists,
    )
    from mailgun.handlers.tags_handler import handle_tags
    from mailgun.handlers.templates_handler import handle_templates
    from mailgun.handlers.users_handler import handle_users

logging.disable(logging.CRITICAL)

HandlerType = Callable[..., Any]

_ALL_HANDLERS: list[HandlerType] = [
    handle_address_validate,
    handle_bounce_classification,
    handle_bounces,
    handle_complaints,
    handle_default,
    handle_domainlist,
    handle_domains,
    handle_inbox,
    handle_ippools,
    handle_ips,
    handle_keys,
    handle_lists,
    handle_metrics,
    handle_resend_message,
    handle_routes,
    handle_tags,
    handle_templates,
    handle_unsubscribes,
    handle_users,
    handle_whitelists,
]

_KNOWN_KWARGS = [
    "_method",
    "action",
    "address",
    "authority_name",
    "bounce_address",
    "checks",
    "comparator",
    "complaint_address",
    "counters",
    "data",
    "dkim",
    "dkim_selector",
    "domain",
    "domain_name",
    "event_types",
    "expression",
    "filters",
    "ip",
    "key_id",
    "limit",
    "limits",
    "list_name",
    "login",
    "member_address",
    "method",
    "multiple",
    "password",
    "pool_id",
    "route_id",
    "skip",
    "storage_url",
    "subaccount_id",
    "tag",
    "tag_name",
    "tags",
    "template_name",
    "test_id",
    "url",
    "usage",
    "user_id",
    "verify",
    "versions",
    "webhook_id",
    "webhook_name",
    "whitelist_address",
]

_PATH_ATTACK_SEEDS = [
    "../",
    "..\\",
    "%2e%2e%2f",
    "%2e%2e/",
    "..%2f",
    "%252e%252e%252f",
    "....//",
    "/absolute/root",
    "C:\\windows\\system32",
    "\x00",
    "\x01\x00\x00\x00\x00\x00\x00\x01",
    "https://attacker.evil/%2f..",
    "xn--eckwd4c7c.xn--zckzah",
]


def _generate_chaotic_value(fdp: atheris.FuzzedDataProvider, depth: int = 0) -> Any:
    """Structure-aware chaotic payload generator."""
    if depth > 3:
        return fdp.ConsumeUnicodeNoSurrogates(16)

    choice = fdp.ConsumeIntInRange(0, 7)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(64)
    if choice == 1:
        return fdp.PickValueInList(_PATH_ATTACK_SEEDS)
    if choice == 2:
        return fdp.ConsumeIntInRange(-2147483648, 2147483647)
    if choice == 3:
        return fdp.ConsumeBool()
    if choice == 4:
        return None
    if choice == 5:
        return [
            _generate_chaotic_value(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 4))
        ]
    if choice == 6:
        return {
            fdp.ConsumeUnicodeNoSurrogates(12): _generate_chaotic_value(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        }
    return fdp.ConsumeBytes(16)


def TestOneInput(data: bytes) -> None:
    if len(data) < 12:
        return

    fdp = atheris.FuzzedDataProvider(data)

    handler: Any
    if fdp.ConsumeIntInRange(1, 100) <= 15:
        handler = handle_default
    else:
        handler = fdp.PickValueInList(_ALL_HANDLERS)

    # Base URL configuration variants
    base_choice = fdp.ConsumeIntInRange(0, 4)
    if base_choice == 0:
        base_url = "https://api.mailgun.net/v3"
    elif base_choice == 1:
        base_url = "https://api.eu.mailgun.net/v4"
    elif base_choice == 2:
        base_url = fdp.ConsumeUnicodeNoSurrogates(48)
    elif base_choice == 3:
        base_url = ""
    else:
        base_url = "http://127.0.0.1:8080/prefix"

    # Multi-segment path keys fuzzing
    key_count = fdp.ConsumeIntInRange(0, 4)
    url_keys: list[Any] = []
    for _ in range(key_count):
        if fdp.ConsumeBool():
            url_keys.append(fdp.PickValueInList(_PATH_ATTACK_SEEDS))
        else:
            url_keys.append(fdp.ConsumeUnicodeNoSurrogates(16))

    url_config: dict[str, Any] = {"base": base_url, "keys": url_keys}

    # Structure corruption on url_config itself (10% of inputs)
    if fdp.ConsumeIntInRange(1, 100) <= 10:
        if fdp.ConsumeBool():
            url_config.pop("keys", None)
        else:
            url_config["keys"] = _generate_chaotic_value(fdp, depth=2)

    # Domain fuzzing with path injection and IDN edge cases
    domain: Any = None
    if fdp.ConsumeBool():
        domain_choice = fdp.ConsumeIntInRange(0, 3)
        if domain_choice == 0:
            domain = fdp.ConsumeUnicodeNoSurrogates(32)
        elif domain_choice == 1:
            domain = fdp.PickValueInList(_PATH_ATTACK_SEEDS)
        elif domain_choice == 2:
            domain = "example.com"
        else:
            domain = fdp.ConsumeInt(500)

    # HTTP method variations including casing, whitespace, and injection
    method_choices = [
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "GET",
        "POST",
        "DELETE",
        "HEAD",
        "OPTIONS",
        "get\r\n",
        "post ",
        None,
    ]
    method: Any = fdp.PickValueInList(method_choices)

    kwargs: dict[str, Any] = {}
    num_kwargs = fdp.ConsumeIntInRange(0, 7)
    for _ in range(num_kwargs):
        key = (
            fdp.PickValueInList(_KNOWN_KWARGS)
            if fdp.ConsumeBool()
            else fdp.ConsumeUnicodeNoSurrogates(12)
        )

        if key == "event_types":
            kwargs[key] = [
                fdp.ConsumeUnicodeNoSurrogates(8)
                for _ in range(fdp.ConsumeIntInRange(1, 4))
            ]
        elif key == "filters" and fdp.ConsumeBool():
            kwargs[key] = {
                "url": fdp.ConsumeUnicodeNoSurrogates(24),
                "resolution": fdp.PickValueInList(["hour", "day", "month", None]),
            }
        else:
            kwargs[key] = _generate_chaotic_value(fdp)

    # Test method parameter priority: method vs _method
    if fdp.ConsumeBool():
        kwargs["_method"] = method
        method = None

    try:
        result = handler(url_config, domain, method, **kwargs)
        if not isinstance(result, str):
            handler_name = getattr(handler, "__name__", type(handler).__name__)
            raise RuntimeError(
                f"CONTRACT VIOLATION: Handler {handler_name} returned non-string: {type(result)}"
            )
    except (ApiError, TypeError, ValueError):
        # Expected rejections for malformed URLs, missing keys, or unsupported methods
        pass
    except Exception as e:
        handler_name = getattr(handler, "__name__", type(handler).__name__)
        raise RuntimeError(
            f"UNHANDLED CRASH in {handler_name} with kwargs {list(kwargs.keys())}: {e}"
        ) from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

#!/usr/bin/env python3
"""
Fuzz test for Mailgun API Route Handlers.
Focus: Deep Path Traversal, Template Injection, and Structure-Aware Type Confusion.
"""

import atexit
import logging
import sys
from typing import Any, Callable

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
    "bounce_address",
    "checks",
    "complaint_address",
    "counters",
    "data",
    "domain",
    "domain_name",
    "event_types",
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


def _generate_chaotic_value(fdp: atheris.FuzzedDataProvider, depth: int = 0) -> Any:
    """
    Structure-Aware Fuzzing Breakthrough:
    Generates valid Python structures (dicts, lists, primitives) filled with chaotic data.
    This bypasses initial type-checkers to penetrate deep URL interpolation logic.
    """
    if depth > 2:  # Prevent infinite recursion depth
        return fdp.ConsumeUnicodeNoSurrogates(16)

    choice = fdp.ConsumeIntInRange(0, 5)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(64)  # XSS/Path Traversal Strings
    elif choice == 1:
        return fdp.ConsumeInt(1000)  # Overflows/Negative ints
    elif choice == 2:
        return fdp.ConsumeBool()  # Booleans
    elif choice == 3:
        return None  # Null injection
    elif choice == 4:
        # Fuzzed List
        return [
            _generate_chaotic_value(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        ]
    else:
        # Fuzzed Dictionary
        return {
            fdp.ConsumeUnicodeNoSurrogates(10): _generate_chaotic_value(fdp, depth + 1)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        }


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)

    handler: Any
    if fdp.ConsumeIntInRange(1, 100) <= 20:
        handler = fdp.ConsumeUnicodeNoSurrogates(16)
    else:
        handler = fdp.PickValueInList(_ALL_HANDLERS)

    url_config: dict[str, Any] = {
        "base": fdp.ConsumeUnicodeNoSurrogates(32) or "https://api.mailgun.net/v3",
        "keys": [
            fdp.ConsumeUnicodeNoSurrogates(16)
            for _ in range(fdp.ConsumeIntInRange(0, 3))
        ],
    }

    domain: str | None = (
        fdp.ConsumeUnicodeNoSurrogates(32) if fdp.ConsumeBool() else None
    )
    method: str | None = fdp.PickValueInList(
        ["delete", "get", "patch", "post", "put", None]
    )

    kwargs: dict[str, Any] = {}
    for _ in range(fdp.ConsumeIntInRange(0, 5)):
        key = (
            fdp.PickValueInList(_KNOWN_KWARGS)
            if fdp.ConsumeBool()
            else fdp.ConsumeUnicodeNoSurrogates(10)
        )

        # Structure-aware injection for V4 Webhook upgrades
        if key == "event_types":
            kwargs[key] = [
                fdp.ConsumeUnicodeNoSurrogates(5),
                fdp.ConsumeUnicodeNoSurrogates(5),
            ]
        elif key == "filters" and fdp.ConsumeBool():
            kwargs[key] = {"url": fdp.ConsumeUnicodeNoSurrogates(20)}
        else:
            kwargs[key] = _generate_chaotic_value(fdp)

    # Randomize method vs _method parameter binding (Testing our recent fix)
    method_val = fdp.PickValueInList(["delete", "get", "patch", "post", "put", None])
    if fdp.ConsumeBool():
        kwargs["_method"] = method_val
        method = None
    else:
        method = method_val

    try:
        result = handler(url_config, domain, method, **kwargs)
        if not isinstance(result, str):
            handler_name = getattr(handler, "__name__", type(handler).__name__)
            raise RuntimeError(
                f"CRASH: Handler {handler_name} returned non-string: {type(result)}"
            )

    except (ApiError, AttributeError, KeyError, TypeError, ValueError):
        # SECURITY SUCCESS: Intercepted malformed path combinations
        pass
    except Exception as e:
        handler_name = getattr(handler, "__name__", type(handler).__name__)
        raise RuntimeError(f"UNHANDLED CRASH in {handler_name}: {e}") from e


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atexit.register(lambda: logging.disable(logging.CRITICAL))
    atheris.Fuzz()

"""Provide a Python SDK for interacting with the Mailgun API.

This package exposes the primary client classes, fluent builders, and
custom exceptions needed to securely integrate with Mailgun's services.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from mailgun.builders import MailgunMessageBuilder, MailgunTemplateBuilder
    from mailgun.client import AsyncClient, Client
    from mailgun.handlers.error_handler import (
        ApiError,
        DeliverabilityError,
        MailgunTimeoutError,
        RouteNotFoundError,
        UploadError,
    )

    __version__: str


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "ApiError": ("mailgun.handlers.error_handler", "ApiError"),
    "AsyncClient": ("mailgun.client", "AsyncClient"),
    "Client": ("mailgun.client", "Client"),
    "DeliverabilityError": ("mailgun.handlers.error_handler", "DeliverabilityError"),
    "MailgunMessageBuilder": ("mailgun.builders", "MailgunMessageBuilder"),
    "MailgunTemplateBuilder": ("mailgun.builders", "MailgunTemplateBuilder"),
    "MailgunTimeoutError": ("mailgun.handlers.error_handler", "MailgunTimeoutError"),
    "RouteNotFoundError": ("mailgun.handlers.error_handler", "RouteNotFoundError"),
    "UploadError": ("mailgun.handlers.error_handler", "UploadError"),
}

# Defines the root public API of the Mailgun SDK
__all__ = [
    "ApiError",
    "AsyncClient",
    "Client",
    "DeliverabilityError",
    "MailgunMessageBuilder",
    "MailgunTemplateBuilder",
    "MailgunTimeoutError",
    "RouteNotFoundError",
    "UploadError",
    "__version__",
]

_SUBMODULE_LOADERS: dict[str, Callable[[], Any]] = {
    "mailgun._httpx_compat": lambda: importlib.import_module("mailgun._httpx_compat"),
    "mailgun._version": lambda: importlib.import_module("mailgun._version"),
    "mailgun.builders": lambda: importlib.import_module("mailgun.builders"),
    "mailgun.client": lambda: importlib.import_module("mailgun.client"),
    "mailgun.config": lambda: importlib.import_module("mailgun.config"),
    "mailgun.endpoints": lambda: importlib.import_module("mailgun.endpoints"),
    "mailgun.filters": lambda: importlib.import_module("mailgun.filters"),
    "mailgun.handlers": lambda: importlib.import_module("mailgun.handlers"),
    "mailgun.handlers.error_handler": lambda: importlib.import_module(
        "mailgun.handlers.error_handler",
    ),
    "mailgun.logger": lambda: importlib.import_module("mailgun.logger"),
    "mailgun.routes": lambda: importlib.import_module("mailgun.routes"),
    "mailgun.security": lambda: importlib.import_module("mailgun.security"),
    "mailgun.types": lambda: importlib.import_module("mailgun.types"),
}

_LAZY_SUBMODULES: frozenset[str] = frozenset(
    {
        "builders",
        "client",
        "config",
        "endpoints",
        "filters",
        "handlers",
        "logger",
        "routes",
        "security",
        "types",
    },
)


def _import_known_submodule(module_name: str) -> Any:
    """Import an allowlisted internal submodule using string literals only.

    Returns:
        Any: The imported internal submodule object.

    Raises:
        ImportError: If ``module_name`` is not in the allowlist.
    """
    loader = _SUBMODULE_LOADERS.get(module_name)
    if loader is None:
        msg = f"Disallowed lazy submodule: {module_name!r}"
        raise ImportError(msg)
    return loader()


def __getattr__(name: str) -> Any:
    """Resolve top-level SDK exports and submodules lazily via PEP 562.

    Returns:
        Any: The resolved class, submodule, or version string.

    Raises:
        AttributeError: If ``name`` is not a public export or lazy submodule.
    """
    if name == "__version__":
        try:
            version_mod = _import_known_submodule("mailgun._version")
            value = version_mod.__version__
        except ImportError:
            value = "0.0.0-unknown"
        globals()[name] = value
        return value

    if name in _LAZY_SUBMODULES:
        submod = _import_known_submodule(f"mailgun.{name}")
        globals()[name] = submod
        return submod

    target = _LAZY_EXPORTS.get(name)
    if target is None:
        msg = f"module 'mailgun' has no attribute {name!r}"
        raise AttributeError(msg)

    module_name, attr_name = target
    value = getattr(_import_known_submodule(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return top-level exports including lazy attributes for introspection tools.

    Returns:
        list[str]: Sorted list of exposed attributes.
    """
    return sorted({*globals(), *__all__, "__version__"})

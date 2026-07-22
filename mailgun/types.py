"""Type aliases and structural contracts for the Mailgun Python SDK."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NotRequired, TypeAlias, TypedDict, Union

from requests.models import Response  # pyright: ignore[reportMissingModuleSource]


if TYPE_CHECKING:
    from mailgun._httpx_compat import Timeout as HttpxTimeout
    from mailgun._httpx_compat import httpx

# ---------------------------------------------------------
# Security, Endpoints & Client Types
# ---------------------------------------------------------
TimeoutType: TypeAlias = Union[float, tuple[float, float], "HttpxTimeout", None]
APIResponseType: TypeAlias = Response | Any
AsyncAPIResponseType: TypeAlias = Union["httpx.Response", Any]

# ---------------------------------------------------------
# Routing Types
# ---------------------------------------------------------
ExactRouteType: TypeAlias = dict[str, tuple[str, tuple[str, ...]]]
PrefixRoutesType: TypeAlias = dict[str, tuple[str, str, str | None]]
DomainsAliasType: TypeAlias = dict[str, str]
DomainsEndpointsType: TypeAlias = dict[str, tuple[str, ...]]
DeprecatedRoutesType: TypeAlias = dict[re.Pattern[str], str]

# ---------------------------------------------------------
# Strict Payload Schemas (DX & Compile-Time Safety)
# ---------------------------------------------------------

# We use the functional syntax for TypedDict here. This allows us to use "from",
# which is a reserved Python keyword and cannot be defined as a class attribute.
SendMessagePayload = TypedDict(
    "SendMessagePayload",
    {
        "to": str | list[str],
        "from": NotRequired[str],
        "cc": NotRequired[str | list[str]],
        "bcc": NotRequired[str | list[str]],
        "subject": NotRequired[str],
        "text": NotRequired[str],
        "html": NotRequired[str],
        "amp_html": NotRequired[str],
        "template": NotRequired[str],
    },
)


class DomainConfig(TypedDict):
    """Schema for Domain Creation/Updates."""

    name: str
    smtp_password: NotRequired[str]
    spam_action: NotRequired[str]
    wildcard: NotRequired[bool]
    force_dkim_authority: NotRequired[bool]
    ips: NotRequired[list[str]]
    web_scheme: NotRequired[str]

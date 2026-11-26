"""Mailgun webhook signature verification and payload parsing helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from mailgun.handlers.error_handler import ApiError
from mailgun.security import SecurityGuard


__all__ = [
    "WebhookPayload",
    "WebhookSignatureData",
    "WebhookVerificationError",
    "parse_webhook_event",
    "verify_webhook_payload",
    "verify_webhook_signature",
]


class WebhookVerificationError(ApiError):
    """Raised when a Mailgun webhook payload or signature fails verification."""


class WebhookSignatureData(TypedDict):
    """Signature metadata block included in Mailgun webhook payloads."""

    timestamp: str | int
    token: str
    signature: str


WebhookPayload = TypedDict(
    "WebhookPayload",
    {
        "signature": WebhookSignatureData,
        "event-data": NotRequired[dict[str, Any]],
    },
)


def _decode_payload_mapping(payload: Mapping[str, Any] | bytes | str) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload

    if isinstance(payload, bytes):
        try:
            raw_text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            msg = "Webhook payload is not valid UTF-8."
            raise WebhookVerificationError(msg) from exc
    else:
        raw_text = payload

    try:
        decoded = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        msg = "Webhook payload is not valid JSON."
        raise WebhookVerificationError(msg) from exc

    if not isinstance(decoded, Mapping):
        msg = "Webhook JSON payload must decode to a JSON object."
        raise WebhookVerificationError(msg)

    return decoded


def _extract_signature_parts(
    data: Mapping[str, Any],
) -> tuple[str, str | int, str, bool]:
    sig_obj = data.get("signature")
    if isinstance(sig_obj, Mapping):
        token = sig_obj.get("token")
        timestamp = sig_obj.get("timestamp")
        signature = sig_obj.get("signature")
        is_envelope = True
    else:
        token = data.get("token")
        timestamp = data.get("timestamp")
        signature = data.get("signature")
        is_envelope = False

    if (
        not isinstance(token, str)
        or not isinstance(signature, str)
        or isinstance(timestamp, bool)
        or not isinstance(timestamp, (str, int))
    ):
        msg = "Webhook payload is missing valid signature fields (token, timestamp, signature)."
        raise WebhookVerificationError(msg)

    return token, timestamp, signature, is_envelope


def verify_webhook_signature(
    signing_key: str | bytes,
    token: str,
    timestamp: str | int,
    signature: str,
    *,
    max_age_seconds: int = 900,
) -> bool:
    """Cryptographically verify a Mailgun webhook signature.

    Args:
        signing_key: Mailgun webhook signing key.
        token: Token string from the webhook signature block.
        timestamp: Timestamp string or integer from the webhook signature block.
        signature: Hex-encoded HMAC-SHA256 signature from the webhook payload.
        max_age_seconds: Maximum allowed age in seconds (default 900; ``<= 0`` disables TTL).

    Returns:
        bool: ``True`` if the signature is valid and within TTL, ``False`` otherwise.
    """
    return SecurityGuard.verify_webhook(
        signing_key=signing_key,
        token=token,
        timestamp=timestamp,
        signature=signature,
        max_age_seconds=max_age_seconds,
    )


def verify_webhook_payload(
    payload: Mapping[str, Any] | bytes | str,
    signing_key: str | bytes,
    *,
    max_age_seconds: int = 900,
) -> bool:
    """Verify a Mailgun webhook JSON envelope or flat form mapping.

    Args:
        payload: Parsed mapping or raw JSON ``str`` / ``bytes`` webhook payload.
        signing_key: Mailgun webhook signing key.
        max_age_seconds: Maximum allowed age in seconds (default 900; ``<= 0`` disables TTL).

    Returns:
        bool: ``True`` when the payload is well-formed and the signature is valid.
    """
    try:
        data = _decode_payload_mapping(payload)
        token, timestamp, signature, _ = _extract_signature_parts(data)
        return verify_webhook_signature(
            signing_key,
            token,
            timestamp,
            signature,
            max_age_seconds=max_age_seconds,
        )
    except (WebhookVerificationError, TypeError, ValueError):
        return False


def parse_webhook_event(
    payload: Mapping[str, Any] | bytes | str,
    signing_key: str | bytes,
    *,
    max_age_seconds: int = 900,
) -> dict[str, Any]:
    """Verify and extract a Mailgun webhook event dictionary.

    Args:
        payload: Parsed mapping or raw JSON ``str`` / ``bytes`` webhook payload.
        signing_key: Mailgun webhook signing key.
        max_age_seconds: Maximum allowed age in seconds (default 900; ``<= 0`` disables TTL).

    Returns:
        dict[str, Any]: Shallow copy of ``event-data`` for JSON envelopes, or the flat payload dict.

    Raises:
        WebhookVerificationError: If the payload is malformed, expired, or has an invalid signature.
    """
    data = _decode_payload_mapping(payload)
    token, timestamp, signature, is_envelope = _extract_signature_parts(data)

    try:
        is_valid = verify_webhook_signature(
            signing_key,
            token,
            timestamp,
            signature,
            max_age_seconds=max_age_seconds,
        )
    except (TypeError, ValueError) as exc:
        msg = "Invalid webhook signature parameters."
        raise WebhookVerificationError(msg) from exc

    if not is_valid:
        msg = "Webhook signature verification failed or timestamp expired."
        raise WebhookVerificationError(msg)

    if is_envelope:
        event_data = data.get("event-data")
        if not isinstance(event_data, Mapping):
            msg = "Webhook envelope is missing a valid 'event-data' mapping."
            raise WebhookVerificationError(msg)
        return dict(event_data)

    return dict(data)

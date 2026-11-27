"""Unit tests for mailgun.webhooks signature verification and payload parsing."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from mailgun.handlers.error_handler import ApiError
from mailgun.webhooks import (
    WebhookVerificationError,
    parse_webhook_event,
    verify_webhook_payload,
    verify_webhook_signature,
)


def _sign(signing_key: str | bytes, timestamp: str | int, token: str) -> str:
    key_bytes = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
    msg = f"{timestamp}{token}".encode()
    return hmac.new(key=key_bytes, msg=msg, digestmod=hashlib.sha256).hexdigest()


def test_webhook_verification_error_inherits_api_error_without_slots() -> None:
    assert issubclass(WebhookVerificationError, ApiError)
    err = WebhookVerificationError("bad sig")
    assert hasattr(err, "__dict__")


def test_verify_webhook_signature_valid_invalid_and_ttl() -> None:
    key = "test-signing-key"
    now = int(time.time())
    token = "tok-123"
    sig = _sign(key, now, token)

    assert verify_webhook_signature(key, token, str(now), sig) is True
    assert verify_webhook_signature(key.encode("utf-8"), token, now, sig) is True
    assert verify_webhook_signature(key, token, now, "0" * 64) is False

    old_ts = now - 3600
    old_sig = _sign(key, old_ts, token)
    assert verify_webhook_signature(key, token, old_ts, old_sig, max_age_seconds=900) is False
    assert verify_webhook_signature(key, token, old_ts, old_sig, max_age_seconds=0) is True


def test_verify_webhook_payload_envelope_and_flat_formats() -> None:
    key = "webhook-key"
    now = str(int(time.time()))
    token = "abc-token"
    sig = _sign(key, now, token)

    envelope = {
        "signature": {"timestamp": now, "token": token, "signature": sig},
        "event-data": {"event": "delivered", "recipient": "user@example.com"},
    }
    assert verify_webhook_payload(envelope, key) is True
    assert verify_webhook_payload(json.dumps(envelope), key) is True
    assert verify_webhook_payload(json.dumps(envelope).encode("utf-8"), key) is True

    flat = {"timestamp": now, "token": token, "signature": sig, "event": "opened"}
    assert verify_webhook_payload(flat, key) is True


def test_verify_webhook_payload_rejects_malformed_and_tampered() -> None:
    key = "webhook-key"
    now = str(int(time.time()))
    token = "abc-token"
    sig = _sign(key, now, token)

    assert verify_webhook_payload({"signature": {"timestamp": now, "token": token, "signature": "bad"}}, key) is False
    assert verify_webhook_payload("{not-json", key) is False
    assert verify_webhook_payload(b"\xff\xfe", key) is False
    assert verify_webhook_payload("[1, 2, 3]", key) is False
    assert verify_webhook_payload({"timestamp": True, "token": token, "signature": sig}, key) is False
    assert verify_webhook_payload({"token": token}, key) is False


def test_parse_webhook_event_envelope_and_flat() -> None:
    key = "webhook-key"
    now = str(int(time.time()))
    token = "tok-xyz"
    sig = _sign(key, now, token)

    event_data = {"event": "clicked", "url": "https://example.com"}
    envelope = {
        "signature": {"timestamp": now, "token": token, "signature": sig},
        "event-data": event_data,
    }
    parsed = parse_webhook_event(envelope, key)
    assert parsed == event_data
    parsed["event"] = "mutated"
    assert event_data["event"] == "clicked"

    flat = {"timestamp": now, "token": token, "signature": sig, "event": "bounced"}
    parsed_flat = parse_webhook_event(json.dumps(flat), key)
    assert parsed_flat == flat


def test_parse_webhook_event_raises_on_invalid_or_missing_event_data() -> None:
    key = "webhook-key"
    now = str(int(time.time()))
    token = "tok-xyz"
    sig = _sign(key, now, token)

    with pytest.raises(WebhookVerificationError, match="not valid JSON"):
        parse_webhook_event("{invalid", key)

    with pytest.raises(WebhookVerificationError, match="not valid UTF-8"):
        parse_webhook_event(b"\xff\xfe", key)

    with pytest.raises(WebhookVerificationError, match="JSON object"):
        parse_webhook_event("[]", key)

    with pytest.raises(WebhookVerificationError, match="signature verification failed"):
        parse_webhook_event(
            {
                "signature": {"timestamp": now, "token": token, "signature": "bad"},
                "event-data": {"event": "delivered"},
            },
            key,
        )

    with pytest.raises(WebhookVerificationError, match="event-data"):
        parse_webhook_event(
            {"signature": {"timestamp": now, "token": token, "signature": sig}},
            key,
        )

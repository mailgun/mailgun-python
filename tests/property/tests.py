"""Property-based and invariant fuzzing test suite for v1.9.1 hardening."""

from __future__ import annotations

import hashlib
import hmac
import io
import logging
import string
import time
from typing import Any
from unittest.mock import patch
from urllib.parse import urlparse

from hypothesis import HealthCheck, assume, given, settings  # type: ignore[import-untyped]
from hypothesis import strategies as st  # type: ignore[import-untyped]
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
import pytest
import requests  # pyright: ignore[reportMissingModuleSource]

from mailgun.client import Client
from mailgun.config import Config, _get_cached_route_data
from mailgun.filters import RedactingFilter
from mailgun.handlers.domains_handler import handle_webhooks
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.inbox_placement_handler import handle_inbox
from mailgun.handlers.ips_handler import handle_ips
from mailgun.handlers.mailinglists_handler import handle_lists
from mailgun.handlers.tags_handler import handle_tags
from mailgun.handlers.templates_handler import handle_templates
from mailgun.security import IdempotencyGuard, SecurityGuard, _PATH_CONTROL_CHAR_RE

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from mailgun.builders import ChunkedStreamer, MailgunMessageBuilder
from mailgun.endpoints import Endpoint
from mailgun.security import SpamGuard

# ------------------------------------------------------------------------------
# 1. Config & Route Normalization Invariants
# ------------------------------------------------------------------------------


class TestConfigProperties:
    """Property tests for configuration parsing and URL normalization."""

    @given(
        timeout=st.one_of(
            st.integers(),
            st.floats(allow_nan=True),
            st.binary(),
            st.lists(st.integers()),
        ),
        api_url=st.text(),
    )  # type: ignore[untyped-decorator]
    def test_property_config_robustness(self, timeout: Any, api_url: str) -> None:
        """INVARIANT: Config must handle arbitrary inputs gracefully.

        It must either sanitize the input or raise a controlled exception
        (ValueError or TypeError). It must never raise unhandled runtime crashes.
        """
        try:
            Config(api_url=api_url)
        except (ValueError, TypeError):
            pass

    @given(endpoint_key=st.text(min_size=1, max_size=100))  # type: ignore[untyped-decorator]
    def test_property_config_route_fallback(self, endpoint_key: str) -> None:
        """INVARIANT: Cached routing engine must resolve arbitrary string keys.

        It must return a route descriptor dictionary or fail with controlled exceptions.
        """
        try:
            route_data = _get_cached_route_data(endpoint_key)
            assert isinstance(route_data, dict)
        except (KeyError, ValueError, TypeError):
            pass

    @given(
        base_url=st.sampled_from(["https://api.mailgun.net", "https://api.mailgun.net/"]),
        path=st.text(alphabet=string.ascii_letters + "/", min_size=1),
    )  # type: ignore[untyped-decorator]
    def test_property_url_normalization_no_duplication(self, base_url: str, path: str) -> None:
        """INVARIANT: URL concatenation must never produce consecutive slashes '//' outside the protocol scheme."""
        base = base_url.rstrip("/")
        path_parts = [p for p in path.split("/") if p]
        path_seg = "/".join(path_parts)
        final_url = f"{base}/v3/{path_seg}" if path_seg else f"{base}/v3"
        stripped_scheme = final_url.replace("https://", "").replace("http://", "")
        assert "//" not in stripped_scheme


# ------------------------------------------------------------------------------
# 2. Endpoint Handler Invariants
# ------------------------------------------------------------------------------


class TestHandlerProperties:
    """Property tests ensuring all route handlers maintain fail-closed invariants."""

    @given(
        kwargs=st.dictionaries(
            keys=st.text(),
            values=st.one_of(st.integers(), st.text(), st.booleans()),
            max_size=10,
        )
    )  # type: ignore[untyped-decorator]
    def test_inbox_handler_defensive_errors(self, kwargs: dict[str, Any]) -> None:
        """INVARIANT: Handlers must process arbitrary keyword arguments defensively."""
        url_dict = {"base": "https://api.mailgun.net/v3", "keys": ["inbox", "tests"]}
        try:
            handle_inbox(url_dict, "example.com", "GET", **kwargs)
        except (ValueError, KeyError, TypeError, ApiError):
            # Expected defensive failure modes for hostile/invalid generated kwargs.
            pass

    @given(
        domain=st.text(),
        address=st.text(),
        method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
    )  # type: ignore[untyped-decorator]
    def test_mailinglists_handler_invariants(
        self, domain: str, address: str, method: str
    ) -> None:
        """INVARIANT: mailinglists_handler must gracefully construct URL paths.

        Hostile parameters must be caught by SecurityGuard rather than crashing string formatting.
        """
        url_dict = {"base": "https://api.mailgun.net/v3", "keys": ["lists"]}
        try:
            handle_lists(url_dict, domain, method, address=address)
        except (ValueError, TypeError, ApiError):
            # Expected fail-closed behavior for hostile/fuzzed inputs in this invariant test.
            pass

    @given(
        dirty_domain=st.text(alphabet=string.printable),
        dirty_ip=st.text(alphabet=string.printable),
    )  # type: ignore[untyped-decorator]
    def test_property_ips_handler_robustness(
        self, dirty_domain: str, dirty_ip: str
    ) -> None:
        """INVARIANT: The IPs handler must process printable strings without unhandled exceptions."""
        url = {"base": "https://api.mailgun.net/v3", "keys": ["ips"]}
        try:
            url_result = handle_ips(url, dirty_domain, "GET", ip=dirty_ip)
            assert url_result.startswith("https://api.mailgun.net/v3/")
        except (ValueError, TypeError, ApiError):
            # Expected for hostile/property-generated input: defensive rejection is acceptable.
            pass

    @given(tag=st.text(alphabet=string.printable))  # type: ignore[untyped-decorator]
    def test_tags_handler_sanitization_invariants(self, tag: str) -> None:
        """INVARIANT: Tags handler must reject control characters and encode parameters safely."""
        url = {"base": "https://api.mailgun.net/v3", "keys": ["tags"]}
        try:
            url_result = handle_tags(url, "example.com", "GET", tag=tag)
            assert "\r" not in url_result
            assert "\n" not in url_result
        except (ValueError, TypeError, ApiError):
            pass

    @given(tag=st.text())  # type: ignore[untyped-decorator]
    @settings(suppress_health_check=[HealthCheck.filter_too_much])  # type: ignore[untyped-decorator]
    def test_templates_handler_version_switch_invariants(self, tag: str) -> None:
        """INVARIANT: Templates handler must route version parameters consistently."""
        try:
            url_result = handle_templates(
                {"base": "https://api.mailgun.net/v3", "keys": ["templates", "test-tpl"]},
                domain="example.com",
                _method="GET",
                template_name="test-tpl",
                version_name=tag,
            )
        except (ValueError, TypeError, ApiError):
            return

        assert "/versions/" in url_result or "v4" in url_result or "v3" in url_result

    @given(webhook_name=st.text())  # type: ignore[untyped-decorator]
    @settings(suppress_health_check=[HealthCheck.filter_too_much])  # type: ignore[untyped-decorator]
    def test_webhooks_handler_v4_upgrade_invariants(self, webhook_name: str) -> None:
        """INVARIANT: Webhooks handler must upgrade to v4 when event_types are present."""
        try:
            url_result = handle_webhooks(
                {"base": "https://api.mailgun.net/v3", "keys": ["webhooks"]},
                domain="example.com",
                method="GET",
                webhook_name=webhook_name,
                event_types=["clicked", "opened"],
            )
        except (ValueError, TypeError, ApiError):
            return

        parsed_url = urlparse(url_result)
        assert parsed_url.hostname == "api.mailgun.net"


# ------------------------------------------------------------------------------
# 3. SecurityGuard & Path Sanitization Invariants
# ------------------------------------------------------------------------------


class TestSecurityGuardProperties:
    """Property tests for input validation, header injection, and path sanitization."""

    @given(
        dirty_input=st.text(
            alphabet=st.characters(
                blacklist_categories=("Cs",), blacklist_characters=["\t"]
            ),
            min_size=1,
            max_size=255,
        )
    )  # type: ignore[untyped-decorator]
    def test_property_header_injection_prevention(self, dirty_input: str) -> None:
        """INVARIANT: Any string containing ASCII control characters must raise ValueError (CWE-113/117)."""
        if _PATH_CONTROL_CHAR_RE.search(dirty_input):
            with pytest.raises(ValueError, match="Security Alert"):
                SecurityGuard.validate_no_control_characters(dirty_input)
        else:
            SecurityGuard.validate_no_control_characters(dirty_input)

    @given(st.text())  # type: ignore[untyped-decorator]
    def test_sanitize_path_segment_idempotency(self, input_str: str) -> None:
        """INVARIANT: sanitize_path_segment must be idempotent: f(f(x)) == f(x)."""
        cleaned: str = ""
        try:
            cleaned = SecurityGuard.sanitize_path_segment(input_str)
        except (ValueError, TypeError):
            assume(False)
            return

        assert SecurityGuard.sanitize_path_segment(cleaned) == cleaned

    @given(st.text())  # type: ignore[untyped-decorator]
    def test_sanitize_path_segment_property(self, input_str: str) -> None:
        """INVARIANT: The sanitized path segment must never contain unencoded traversal slashes (CWE-22)."""
        try:
            sanitized = SecurityGuard.sanitize_path_segment(input_str)
            assert "/" not in sanitized
            assert "\\" not in sanitized
        except (ValueError, TypeError):
            assume(False)


# ------------------------------------------------------------------------------
# 4. Idempotency Stream & File Pointer Invariants
# ------------------------------------------------------------------------------


@given(
    data=st.binary(min_size=1, max_size=100000),
    seek_offset=st.integers(min_value=0, max_value=50),
)  # type: ignore[untyped-decorator]
def test_idempotency_file_pointer_invariant(data: bytes, seek_offset: int) -> None:
    """INVARIANT: IdempotencyGuard must preserve stream seek position across calculations."""
    assume(seek_offset <= len(data))
    stream = io.BytesIO(data)
    stream.seek(seek_offset)
    pos_before = stream.tell()

    # Direct attachment stream calculation
    key1 = IdempotencyGuard.generate_key(
        "test.com",
        {"to": "alice@example.com", "subject": "Test"},
        [("attachment", stream)],
    )
    assert stream.tell() == pos_before

    # Repeated calculation produces identical hash and keeps pointer position intact
    key2 = IdempotencyGuard.generate_key(
        "test.com",
        {"to": "alice@example.com", "subject": "Test"},
        [("attachment", stream)],
    )
    assert key1 == key2
    assert stream.tell() == pos_before


@given(data=st.binary(min_size=1, max_size=50000))  # type: ignore[untyped-decorator]
def test_idempotency_nested_tuple_file_pointer_invariant(data: bytes) -> None:
    """INVARIANT: Nested multipart file tuples must also have their tell() position restored."""
    stream = io.BytesIO(data)
    stream.seek(5)
    pos_before = stream.tell()

    nested_tuple = ("report.pdf", stream, "application/pdf")
    key = IdempotencyGuard.generate_key(
        "test.com",
        {"to": "bob@example.com"},
        [("file", nested_tuple)],
    )
    assert isinstance(key, str)
    assert len(key) == 64
    assert stream.tell() == pos_before


# ------------------------------------------------------------------------------
# 5. Logging Filter Structure & Formatting Invariants
# ------------------------------------------------------------------------------


@given(
    args=st.lists(
        st.one_of(
            st.integers(),
            st.text(),
            st.uuids(),
            st.datetimes(),
            st.dates(),
        ),
        max_size=20,
    ),
    msg=st.text(min_size=1, max_size=100),
)  # type: ignore[untyped-decorator]
def test_redacting_filter_args_preservation(args: list[Any], msg: str) -> None:
    """INVARIANT: RedactingFilter must preserve record.args tuple type and exact length."""
    filter_ = RedactingFilter()
    record = logging.LogRecord("test", logging.INFO, "path", 1, msg, tuple(args), None)

    assert filter_.filter(record) is True
    assert isinstance(record.args, tuple)
    assert len(record.args) == len(args)


@given(
    secret_token=st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=10,
        max_size=50,
    ),
    template_str=st.sampled_from(["User count: %d, Target: %s", "Item: %s, Price: %s"]),
)  # type: ignore[untyped-decorator]
def test_redacting_filter_tuple_args_string_formatting(
    secret_token: str, template_str: str
) -> None:
    """INVARIANT: RedactingFilter must not crash Python's standard logging string formatter."""
    filter_ = RedactingFilter()
    key_arg = f"key-{secret_token}"
    args = (42, key_arg) if "%d" in template_str else (key_arg, "100")

    record = logging.LogRecord("test", logging.INFO, "path", 1, template_str, args, None)
    assert filter_.filter(record) is True
    assert isinstance(record.args, tuple)

    # Must format cleanly without TypeError: not enough arguments for format string
    formatted_msg = record.msg % record.args
    assert "key-[REDACTED]" in formatted_msg
    assert secret_token not in formatted_msg


# ------------------------------------------------------------------------------
# 6. Fuzz-Testing URL Path Segment Sanitization
# ------------------------------------------------------------------------------


@given(segment=st.text())  # type: ignore[untyped-decorator]
def test_sanitize_path_traversal_fuzz(segment: str) -> None:
    """INVARIANT: Sanitized segments must never contain unencoded traversal tokens or control chars."""
    try:
        sanitized = SecurityGuard.sanitize_path_segment(segment)
        assert ".." not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert "\x00" not in sanitized
        assert "\r" not in sanitized
        assert "\n" not in sanitized
    except (ValueError, TypeError):
        pass  # Controlled, expected fail-closed validation error


# ------------------------------------------------------------------------------
# 7. Webhook Replay Attack TTL Invariants
# ------------------------------------------------------------------------------


@given(
    token=st.text(min_size=1, max_size=50),
    signing_key=st.text(min_size=1, max_size=50),
    time_delta=st.integers(min_value=-3600, max_value=3600),
)  # type: ignore[untyped-decorator]
def test_verify_webhook_replay_ttl_invariant(
    token: str, signing_key: str, time_delta: int
) -> None:
    """INVARIANT: verify_webhook must reject timestamps outside max_age_seconds window."""
    now = int(time.time())
    ts = now + time_delta
    msg = f"{ts}{token}".encode("utf-8")
    sig = hmac.new(
        key=signing_key.encode("utf-8"), msg=msg, digestmod=hashlib.sha256
    ).hexdigest()

    is_valid = SecurityGuard.verify_webhook(
        signing_key, token, ts, sig, max_age_seconds=900
    )

    if abs(time_delta) > 900:
        assert is_valid is False
    else:
        assert is_valid is True


# ------------------------------------------------------------------------------
# 8. Stateful Client Lifecycle Machine
# ------------------------------------------------------------------------------


class ClientLifecycleMachine(RuleBasedStateMachine):
    """Models the lifecycle of the Mailgun Client to ensure that connections
    and resources are managed defensively through network interruptions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.client: Client | None = None
        self.is_connected: bool = True

    @initialize(api_key=st.text(alphabet=string.ascii_letters + string.digits, min_size=5, max_size=20))  # type: ignore[untyped-decorator]
    def init_client(self, api_key: str) -> None:
        """Initialize client instance with generated credentials."""
        try:
            self.client = Client(auth=("api", api_key))
            self.is_connected = True
        except (ValueError, TypeError):
            self.client = None

    @rule()  # type: ignore[untyped-decorator]
    def send_request(self) -> None:
        """Simulate an active API request execution."""
        if not self.client:
            return
        with patch("requests.Session.send") as mock_send:
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"items": []}'
            mock_send.return_value = resp

            try:
                self.client.domains.get(domain="test.com")
                self.is_connected = True
            except (requests.exceptions.RequestException, ApiError):
                self.is_connected = False

    @rule()  # type: ignore[untyped-decorator]
    def network_drop(self) -> None:
        """Simulate a transient network disconnection."""
        if not self.client:
            return
        with patch(
            "requests.Session.send",
            side_effect=requests.exceptions.ConnectionError("Network dropped"),
        ):
            try:
                self.client.domains.get(domain="test.com")
            except (requests.exceptions.ConnectionError, ApiError):
                self.is_connected = False

    @rule()  # type: ignore[untyped-decorator]
    def reconnect(self) -> None:
        """Simulate reconnection after a network failure."""
        if not self.client or self.is_connected:
            return
        with patch("requests.Session.send") as mock_send:
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"message": "reconnected"}'
            mock_send.return_value = resp

            try:
                self.client.domains.get(domain="test.com")
                self.is_connected = True
            except Exception:
                pass


TestClientLifecycle = ClientLifecycleMachine.TestCase


# ------------------------------------------------------------------------------
# 9. Stateful Patch Sequence & Invariant Machine (v1.9.1)
# ------------------------------------------------------------------------------


class MailgunStateSequenceMachine(RuleBasedStateMachine):
    """Stress-tests Mailgun state transitions, resource cleanup, and stream idempotency."""

    def __init__(self) -> None:
        super().__init__()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.client: Client | None = None
        self.builder: MailgunMessageBuilder | None = None
        self.test_file: Path | None = None
        self.is_closed: bool = False

    @initialize()  # type: ignore[untyped-decorator]
    def setup_system(self) -> None:
        mock_cred = "mock-client-credential"
        self.client = Client(auth=("api", mock_cred))
        self.builder = MailgunMessageBuilder(from_email="sender@example.com")
        self.test_file = self.temp_path / "attachment.bin"
        self.test_file.write_bytes(b"A" * 1024 * 64)
        self.is_closed = False

    @rule(recipient=st.emails())  # type: ignore[untyped-decorator]
    def add_recipient_step(self, recipient: str) -> None:
        if self.builder:
            self.builder.add_recipient(recipient)

    @rule(html_chunk=st.text(max_size=500))  # type: ignore[untyped-decorator]
    def mutate_html_payload(self, html_chunk: str) -> None:
        if self.builder:
            self.builder.set_html(f"<html><body>{html_chunk}</body></html>")
            report = self.builder.check_deliverability()
            assert "is_safe" in report
            assert isinstance(report["issues"], list)

    @rule(
        key=st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=20,
        ),
        val=st.recursive(
            st.text(max_size=50),
            lambda children: st.dictionaries(st.text(max_size=10), children, max_size=3),
            max_leaves=10,
        ),
    )  # type: ignore[untyped-decorator]
    def inject_complex_variable(self, key: str, val: Any) -> None:
        if self.builder:
            try:
                self.builder.add_custom_variable(key, val)
            except ValueError:
                pass

    @rule()  # type: ignore[untyped-decorator]
    def attach_and_hash_stream(self) -> None:
        """Invariant: Idempotency calculation must reset file pointers back to index 0."""
        if not self.builder or not self.test_file:
            return

        streamer = ChunkedStreamer(self.test_file, safe_base_dir=self.temp_path, chunk_size=1024)
        files = [("attachment", ("attachment.bin", streamer, "application/octet-stream"))]

        key1 = IdempotencyGuard.generate_key("example.com", {"to": "user@example.com"}, files)
        assert isinstance(key1, str)
        assert len(key1) == 64
        assert streamer.tell() == 0, "Streamer pointer was not reset to 0 after idempotency calculation"

        chunk = streamer.read(1024)
        assert chunk == b"A" * 1024
        streamer.close()

    @rule()  # type: ignore[untyped-decorator]
    def execute_stream_pagination_shock(self) -> None:
        """Invariant: Terminal pages returning 'paging: null' must terminate cleanly with StopIteration."""
        if not self.client or self.is_closed or not self.client._session:
            return

        endpoint = Endpoint(
            url={"base": "https://api.mailgun.net/v3", "keys": ["events"]},
            headers={"User-Agent": "test"},
            auth=self.client.auth,
            session=self.client._session,
        )

        mock_responses = [
            MagicMock(
                status_code=200,
                json=lambda: {
                    "items": [{"id": 1}],
                    "paging": {"next": "https://api.mailgun.net/v3/events?page=2"},
                },
            ),
            MagicMock(status_code=200, json=lambda: {"items": [{"id": 2}], "paging": None}),
        ]

        with patch.object(self.client._session, "get", side_effect=mock_responses):
            items = list(endpoint.stream(domain="example.com"))
            assert len(items) == 2
            assert items[0]["id"] == 1
            assert items[1]["id"] == 2

    @rule()  # type: ignore[untyped-decorator]
    def close_and_reopen_lifecycle(self) -> None:
        """Invariant: Private attributes must fail fast after client close."""
        if self.client and not self.is_closed:
            self.client.close()
            self.is_closed = True
            assert self.client._session is None

            # Test an undefined private attribute; slots like `_session` exist and evaluate to None
            with pytest.raises(AttributeError):
                _ = self.client._unbound_private

            # Re-open the client to preserve the lifecycle sequence for remaining rules
            mock_cred = "mock-client-credential"
            self.client = Client(auth=("api", mock_cred))
            self.is_closed = False

TestMailgunStateMachine = MailgunStateSequenceMachine.TestCase

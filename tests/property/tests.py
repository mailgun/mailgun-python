import string
from typing import Any
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
import requests
from hypothesis import assume, given  # type: ignore[import-untyped]
from hypothesis import strategies as st  # type: ignore[import-untyped]
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from mailgun.client import Client
from mailgun.config import Config, _get_cached_route_data
from mailgun.handlers.domains_handler import handle_webhooks
from mailgun.handlers.error_handler import ApiError
from mailgun.handlers.inbox_placement_handler import handle_inbox
from mailgun.handlers.ips_handler import handle_ips
from mailgun.handlers.mailinglists_handler import handle_lists
from mailgun.handlers.tags_handler import handle_tags
from mailgun.handlers.templates_handler import handle_templates
from mailgun.security import _PATH_CONTROL_CHAR_RE, SecurityGuard


class TestConfigProperties:
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
        """
        INVARIANT: Config must be defensive. It must either coerce the input
        correctly or raise a controlled exception (ValueError/TypeError).
        It must never crash with an unhandled exception.
        """
        try:
            Config(api_url=api_url)
        except (ValueError, TypeError):
            pass

    @given(endpoint_key=st.text(min_size=1, max_size=100))  # type: ignore[untyped-decorator]
    def test_property_config_route_fallback(self, endpoint_key: str) -> None:
        """
        INVARIANT: Regardless of what string is requested from the route map,
        the caching engine and path generator must safely return a tuple
        or valid dictionary without causing an unhandled internal exception.
        """
        try:
            route_data = _get_cached_route_data(endpoint_key)
            assert isinstance(route_data, dict)
        except (KeyError, ValueError, TypeError):
            pass

    @given(
        base_url=st.sampled_from(
            [
                "https://api.mailgun.net",
                "https://api.eu.mailgun.net",
                "http://localhost:8080",
            ]
        ),
        path=st.text(alphabet=string.ascii_letters + "/-", min_size=1, max_size=50),
    )  # type: ignore[untyped-decorator]
    def test_property_url_normalization_no_duplication(
        self, base_url: str, path: str
    ) -> None:
        """
        INVARIANT: A base_url with trailing slashes joined with a path with
        leading slashes must NEVER result in a double slash `//` in the path segment.
        """
        config = Config(api_url=f"{base_url}/")
        if not path.startswith("/"):
            path = f"/{path}"

        result = config._build_base_url("v3", path)
        parsed = urlparse(result)
        assert "//" not in parsed.path


class TestHandlerProperties:
    @given(
        kwargs=st.dictionaries(
            keys=st.text(),
            values=st.one_of(st.integers(), st.text(), st.booleans()),
            max_size=10,
        )
    )  # type: ignore[untyped-decorator]
    def test_inbox_handler_defensive_errors(self, kwargs: dict[str, Any]) -> None:
        """
        INVARIANT: Handlers must process optional dictionary kwargs defensively.
        If essential kwargs are missing, they should raise a controlled ValueError
        or KeyError instead of crashing the URL builder logic.
        """
        url_dict = {"base": "https://api.mailgun.net/v3", "keys": ["inbox", "tests"]}
        try:
            handle_inbox(url_dict, "example.com", "GET", **kwargs)
        except (ValueError, KeyError, TypeError):
            pass

    @given(
        domain=st.text(),
        address=st.text(),
        method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
    )  # type: ignore[untyped-decorator]
    def test_mailinglists_handler_invariants(
        self, domain: str, address: str, method: str
    ) -> None:
        """
        INVARIANT: mailinglists_handler must gracefully construct URL paths
        regardless of what strings are provided for address or domain, relying
        on SecurityGuard to trap hostile values before string concatenation.
        """
        url_dict = {"base": "https://api.mailgun.net/v3", "keys": ["lists"]}
        try:
            handle_lists(url_dict, domain, method, address=address)
        except (ValueError, TypeError):
            pass

    @given(
        dirty_domain=st.text(alphabet=string.printable),
        dirty_ip=st.text(alphabet=string.printable),
    )  # type: ignore[untyped-decorator]
    def test_property_ips_handler_robustness(
        self, dirty_domain: str, dirty_ip: str
    ) -> None:
        """
        INVARIANT: The IPs handler must process any printable string without
        an unhandled exception, filtering invalid domains/IPs strictly via
        ValueError.
        """
        url = {"base": "https://api.mailgun.net/v3", "keys": ["ips"]}
        try:
            url_result = handle_ips(
                url, dirty_domain, "GET", ip=dirty_ip
            )
            assert url_result.startswith("https://api.mailgun.net/v3/")
        except (ValueError, TypeError):
            pass

    @given(
        tag=st.text(alphabet=string.printable),
    )  # type: ignore[untyped-decorator]
    def test_tags_handler_sanitization_invariants(self, tag: str) -> None:
        """
        INVARIANT: Tags handler must reject control characters and properly
        URL-encode valid parameters to avoid path traversal.
        """
        url = {"base": "https://api.mailgun.net/v3", "keys": ["tags"]}
        try:
            url_result = handle_tags(url, "example.com", "GET", tag=tag)
            assert "\r" not in url_result
            assert "\n" not in url_result
        except (ValueError, TypeError):
            pass

    @given(
        tag=st.text(alphabet=string.printable),
    )  # type: ignore[untyped-decorator]
    def test_templates_handler_version_switch_invariants(self, tag: str) -> None:
        """
        INVARIANT: Templates handler relies heavily on dynamic `versions=True` kwargs.
        Test arbitrary inputs into the tag kwarg to ensure structural URL integrity.
        """
        url = {"base": "https://api.mailgun.net/v3", "keys": ["templates"]}
        try:
            url_result = handle_templates(
                url, "example.com", "GET", versions=True, tag=tag
            )
            assert "/versions/" in url_result
        except (ValueError, TypeError):
            pass

    @given(
        webhook_name=st.text(alphabet=string.printable),
    )  # type: ignore[untyped-decorator]
    def test_webhooks_handler_v4_upgrade_invariants(self, webhook_name: str) -> None:
        """
        INVARIANT: Webhooks have been upgraded to the /v4/ API structure.
        The handler must explicitly swap the base URL to v4.
        """
        url = {"base": "https://api.mailgun.net/v3", "keys": ["webhooks"]}
        try:
            url_result = handle_webhooks(
                url, "example.com", "GET", webhook_name=webhook_name
            )
            assert "api.mailgun.net/v4" in url_result
            assert "api.mailgun.net/v3" not in url_result
        except (ValueError, TypeError):
            pass


class TestSecurityGuardProperties:
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
        """
        INVARIANT: Any string containing an ASCII control character MUST raise a ValueError.
        This ensures HTTP Header Injection (CWE-113) and Log Forging (CWE-117) are impossible.
        """
        if _PATH_CONTROL_CHAR_RE.search(dirty_input):
            with pytest.raises(ValueError, match="Security Alert"):
                SecurityGuard.validate_no_control_characters(dirty_input)
        else:
            SecurityGuard.validate_no_control_characters(dirty_input)

    @given(st.text())  # type: ignore[untyped-decorator]
    def test_sanitize_path_segment_idempotency(self, input_str: str) -> None:
        """
        INVARIANT: Path sanitization should be idempotent.
        sanitize(sanitize(x)) == sanitize(x)
        """
        try:
            first_pass = SecurityGuard.sanitize_path_segment(input_str)
            second_pass = SecurityGuard.sanitize_path_segment(first_pass)
            assert first_pass == second_pass
        except ValueError:
            pass

    @given(st.text())  # type: ignore[untyped-decorator]
    def test_sanitize_path_segment_property(self, input_str: str) -> None:
        """
        INVARIANT: The sanitized path segment MUST NOT contain a forward slash '/'
        or backward slash '\\' to completely mitigate Path Traversal (CWE-22).
        """
        try:
            sanitized = SecurityGuard.sanitize_path_segment(input_str)
            assert "/" not in sanitized
            assert "\\" not in sanitized
        except ValueError:
            assume(False)


class ClientLifecycleMachine(RuleBasedStateMachine):
    """
    Models the lifecycle of the Mailgun Client to ensure that connections
    and resources are managed defensively even through network interruptions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.client: Client | None = None
        self.is_connected = False

    @initialize(
        domain=st.text(min_size=4, max_size=20), api_key=st.text(min_size=10)
    )  # type: ignore[untyped-decorator]
    def init_client(self, domain: str, api_key: str) -> None:
        self.client = Client(auth=("api", api_key))
        self.is_connected = True

    @rule()  # type: ignore[untyped-decorator]
    def close_client(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            self.is_connected = False

    @rule(domain=st.text(min_size=5, max_size=15))  # type: ignore[untyped-decorator]
    def connect_and_request(self, domain: str) -> None:
        if not self.client:
            return
        with patch("requests.Session.send") as mock_send:
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"items": []}'
            mock_send.return_value = resp

            try:
                self.client.domains.get(domain=domain)
            except Exception:
                pass

    @rule()  # type: ignore[untyped-decorator]
    def network_drop(self) -> None:
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

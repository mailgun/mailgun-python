import contextlib
import warnings
from unittest.mock import MagicMock, patch

import pytest

from mailgun.client import BaseClient, Client, Config, Endpoint


class TestBaseClientDunders:
    def test_base_client_repr_str_dir(self) -> None:
        client = BaseClient(auth=("api", "key-123"))
        assert repr(client) == "<BaseClient api_url='https://api.mailgun.net'>"
        assert str(client) == "Mailgun BaseClient"
        assert "messages" in dir(client)


class TestClientAttributeAccess:
    def test_client_dir(self) -> None:
        client = Client()
        attrs = dir(client)
        assert "domains" in attrs
        assert "messages" in attrs

    def test_client_getattr_caching_and_dir(self) -> None:
        client = Client(auth=("api", "key"))
        _ = dir(client)
        ep1 = client.domains
        ep2 = client.domains
        assert ep1._url == ep2._url

    def test_client_getattr_ips(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.ips
        assert ep._url["keys"] == ["ips"]

    def test_client_getattr_messages_caching(self) -> None:
        client = Client(auth=("api", "key"))
        _ = dir(client)
        ep1 = client.messages
        ep2 = client.messages
        assert ep1 is not None
        assert ep2 is not None

    def test_client_getattr_returns_endpoint_instance(self) -> None:
        client = Client(auth=("api", "key-123"))
        ep = client.domains
        assert ep is not None
        assert isinstance(ep, Endpoint)
        assert ep._auth == ("api", "key-123")
        assert ep._url["keys"] == ["domains"]


class TestClientClosure:
    def test_client_close(self) -> None:
        client = Client(auth=("api", "key-123"))
        _ = client.messages
        assert client._session is not None
        client.close()
        assert client._session is None

    def test_client_close_is_idempotent(self) -> None:
        client = Client(auth=("api", "key"))
        client.close()
        client.close()

    def test_client_coverage_enhancement(self) -> None:
        client = Client(auth=("api", "key"))
        client.close()
        client.close()

    def test_client_unclosed_resource_warning(self) -> None:
        """Verify that leaving a Client unclosed triggers a ResourceWarning upon deletion."""
        import gc
        client = Client(auth=("api", "key"))
        _ = client._session
        with pytest.warns(ResourceWarning, match="Unclosed Client detected"):
            del client
            gc.collect()

    def test_sync_client_close_clears_auth_and_headers(self) -> None:
        client = Client(auth=("api", "key-123"))
        session = client._session
        client.close()

        assert client._session is None
        assert client.auth is None  # pyright: ignore[reportOptionalMemberAccess]
        assert session.auth is None  # pyright: ignore[reportOptionalMemberAccess]

    def test_client_del_attribute_error(self) -> None:
        """Coverage: Silently catch AttributeError during GC deletion."""
        client = Client(auth=("api", "key"))
        del client._session  # Force the __getattribute__ lookup to fail
        client.__del__()  # Must pass without crashing

    def __del__(self) -> None:
        """Emit a ResourceWarning if the async client is garbage-collected without being closed."""
        with contextlib.suppress(Exception):
            client = object.__getattribute__(self, "_httpx_client")
            if client is not None and not client.is_closed:
                warnings.warn(
                    f"Unclosed {self.__class__.__name__} detected. You must explicitly "
                    "call '.aclose()' or use the 'async with' context manager to prevent "
                    "socket and memory leaks.",
                    ResourceWarning,
                    stacklevel=2,
                )

class TestClientPing:
    def test_sync_client_ping_success(self) -> None:
        client = Client(auth=("api", "key-123"))
        mock_resp = MagicMock(status_code=200)

        with patch("mailgun.client.Endpoint.get", return_value=mock_resp):
            assert client.ping() is True

    def test_sync_ping_network_failure(self) -> None:
        """Hits the except Exception branch inside ping()."""
        client = Client(auth=("api", "key"))
        with patch("mailgun.client.Endpoint.get", side_effect=ConnectionError("Network Down")):
            assert client.ping() is False

    def test_client_init_int_timeout_warning(self) -> None:
        with pytest.warns(DeprecationWarning, match="integer for 'timeout' is deprecated"):
            Client(auth=("api", "key"), timeout=10)


class TestClientContextManager:
    def test_client_context_manager(self) -> None:
        with Client(auth=("api", "key-123")) as client:
            _ = client.messages
            assert client._session is not None
        assert client._session is None

    def test_client_context_manager_clean_exit(self) -> None:
        client = Client(auth=("api", "key"))
        with client:
            _ = client.messages
        assert client._session is None


class TestClientInitialization:
    def test_client_init_default(self) -> None:
        client = Client()
        assert client.auth is None  # pyright: ignore[reportOptionalMemberAccess]
        assert client.config.api_url == Config.DEFAULT_API_URL

    def test_client_init_emits_deprecation_warning_for_api_version(self) -> None:
        with pytest.warns(DeprecationWarning, match="api_version"):
            Client(api_version="v3")  # type: ignore[call-arg]

    def test_client_init_with_api_url(self) -> None:
        client = Client(api_url="https://custom.mailgun.net/")
        assert client.config.api_url == "https://custom.mailgun.net"

    def test_client_init_with_auth(self) -> None:
        client = Client(auth=("api", "key-123"))
        assert client.auth == ("api", "key-123")  # pyright: ignore[reportOptionalMemberAccess]

    def test_sync_ping_network_failure(self) -> None:
        """Hits the except Exception branch inside ping()."""
        with pytest.MonkeyPatch.context() as m:
            m.setattr("requests.Session.request", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("Network Down")))
            client = Client(auth=("api", "key"))
            assert client.ping() is False


class TestErrorHandler:
    """Hits the missing branches in error mapping."""

    def test_timeout_mapping_sync(self) -> None:
        """Ensure requests.exceptions.ReadTimeout maps to MailgunTimeoutError."""
        from requests.exceptions import ReadTimeout  # pyright: ignore[reportMissingModuleSource]

        from mailgun.client import Client
        from mailgun.handlers.error_handler import MailgunTimeoutError

        client = Client(auth=("api", "key-12345"))

        with pytest.raises(MailgunTimeoutError), pytest.MonkeyPatch.context() as m:
            # Force the underlying requests session to throw a ReadTimeout
            m.setattr(
                "requests.Session.request",
                lambda *args, **kwargs: (_ for _ in ()).throw(ReadTimeout("Timeout"))
            )

            client.domains.get(domain="test.com")

    def test_deliverability_error_formatting(self) -> None:
        """Coverage: Ensure the custom SpamGuard exception formats output correctly."""
        from mailgun.handlers.error_handler import DeliverabilityError
        error = DeliverabilityError(score=45.0, issues=["Missing alt tags"])

        assert "Score: 45.0/100" in str(error)
        assert "- Missing alt tags" in str(error)

import pytest

from mailgun.client import Client, Config, Endpoint


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
        assert client.auth is None
        assert client.config.api_url == Config.DEFAULT_API_URL

    def test_client_init_emits_deprecation_warning_for_api_version(self) -> None:
        with pytest.warns(DeprecationWarning, match="api_version"):
            Client(api_version="v3")  # type: ignore[call-arg]

    def test_client_init_with_api_url(self) -> None:
        client = Client(api_url="https://custom.mailgun.net/")
        assert client.config.api_url == "https://custom.mailgun.net"

    def test_client_init_with_auth(self) -> None:
        client = Client(auth=("api", "key-123"))
        assert client.auth == ("api", "key-123")

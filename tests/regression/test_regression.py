import logging
from pathlib import Path

import pytest

from mailgun.client import AsyncClient, Client, Config
from mailgun.logger import get_logger
from mailgun.security import SecurityGuard
from mailgun.builders import MailgunMessageBuilder

CORPUS_ROOT = Path("tests/fuzz/corpus")


def get_corpus_files() -> list[Path]:
    """Recursively discover all corpus artifacts."""
    if not CORPUS_ROOT.exists():
        return []
    return list(CORPUS_ROOT.rglob("*"))


class TestConfigRegression:
    def test_api_url_emits_semantic_warning_on_version_suffix(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            config = Config(api_url="https://api.eu.mailgun.net/v3/")

        assert config._baked_urls["v3"] == "https://api.eu.mailgun.net/v3"
        assert "Semantic Configuration Warning" in caplog.text
        assert "should be the base domain" in caplog.text

    @pytest.mark.parametrize(
        "api_url",
        [
            "https://api.eu.mailgun.net/v3",
            "https://api.eu.mailgun.net/v3/",
            "https://api.eu.mailgun.net/v4",
            "https://api.eu.mailgun.net/v4/",
        ],
        ids=[
            "v3_without_trailing_slash",
            "v3_with_trailing_slash",
            "v4_without_trailing_slash",
            "v4_with_trailing_slash",
        ],
    )
    def test_api_url_with_trailing_version(self, api_url: str) -> None:
        """
        Regression test for #40: v1.7.0 silently broke api_url values containing /v3.
        Tests that an explicitly passed version segment does not result in duplication.
        """
        config = Config(api_url=api_url)

        # Before the fix, this evaluated to 'https://api.eu.mailgun.net/v3/v3' and failed.
        if "mailgun" in api_url:
            assert config._baked_urls["v3"] == "https://api.eu.mailgun.net/v3"
            assert config._baked_urls["v4"] == "https://api.eu.mailgun.net/v4"


class TestControlCharacters:
    @pytest.mark.asyncio
    async def test_async_endpoint_rejects_control_characters(self) -> None:
        """
        Ensure the asynchronous client intercepts control characters injected
        via endpoint kwargs before they crash httpx.
        """
        client = AsyncClient(auth=("api", "key"))

        with pytest.raises(ValueError) as exc:
            await client.messages.get(domain="api\x13.mailgun.net")

        assert "CWE-20" in str(exc.value)
        assert "Forbidden control characters" in str(exc.value)

    @pytest.mark.asyncio
    async def test_semantic_divergence_on_control_chars(self) -> None:
        """
        Regression test for Semantic Divergence between Sync and Async clients
        caused by control characters in path segments (e.g., \x00, \x0b).
        Both must fail-closed natively with a ValueError, not a library-specific error.
        """
        # Payload derived from libFuzzer crash artifacts
        bad_domain = "test\x0bdomain\x00.com"

        sync_client = Client(auth=("api", "key"))
        async_client = AsyncClient(auth=("api", "key"))

        sync_exc = None
        try:
            sync_client.messages.get(domain=bad_domain)
        except ValueError as e:
            sync_exc = e
        except Exception as e:
            pytest.fail(f"Sync client raised wrong exception: {type(e).__name__}")

        async_exc = None
        try:
            await async_client.messages.get(domain=bad_domain)
        except ValueError as e:
            async_exc = e
        except Exception as e:
            pytest.fail(f"Async client raised wrong exception: {type(e).__name__}")

        assert sync_exc is not None, "Sync client failed to reject control characters."
        assert async_exc is not None, "Async client failed to reject control characters."

    def test_sync_endpoint_rejects_control_characters(self) -> None:
        """
        Ensure the synchronous client intercepts control characters injected
        via endpoint kwargs before they reach the requests library.
        """
        client = Client(auth=("api", "key"))

        with pytest.raises(ValueError) as exc:
            # \x13 is Device Control 3, discovered by libFuzzer
            client.messages.get(domain="api\x13.mailgun.net")

        assert "CWE-20" in str(exc.value)
        assert "Forbidden control characters" in str(exc.value)


# class TestCorpusRegression:
#     @pytest.mark.security
#     @pytest.mark.parametrize(
#         "corpus_file", get_corpus_files(), ids=lambda x: x.name
#     )
#     def test_corpus_regression(self, corpus_file: Path) -> None:
#         """
#         Regression test: ensures current code handles historical crash/coverage
#         payloads without unhandled exceptions.
#         """
#         from tests.fuzz.fuzz_client import TestOneInput
#
#         if not corpus_file.is_file():
#             pytest.skip("Not a file")
#
#         with open(corpus_file, "rb") as f:
#             data = f.read()
#
#         # The test passes if it runs without raising a new exception type
#         # not already covered by the fuzzer's internal try/except blocks.
#         # If the fuzzer previously caught a bug here, it won't crash now.
#         TestOneInput(data)


class TestLoggerRegression:
    def test_logger_rejects_reserved_extra_keys(self) -> None:
        """
        Regression Test: Prove that Python's logging module natively rejects
        reserved keys in the `extra` dictionary (like 'message', 'name', 'args').

        This validates that the fuzzer crash was a standard library defensive
        constraint, not a Mailgun SDK vulnerability.
        """
        logger = get_logger("test_reserved_keys")

        # Using .warning() ensures we bypass default INFO-level filters
        # that might prevent the log record from being evaluated at all.
        with pytest.raises(
            KeyError, match="Attempt to overwrite 'message' in LogRecord"
        ):
            logger.warning("Test log", extra={"message": "malicious_override"})

        with pytest.raises(
            KeyError, match="Attempt to overwrite 'levelname' in LogRecord"
        ):
            logger.warning("Test log", extra={"levelname": "CRITICAL"})


class TestPathTraversal:
    @pytest.mark.asyncio
    async def test_async_client_rejects_tab_in_webhook_name(self) -> None:
        """Regression Test for Fuzzer Crash: Invalid non-printable ASCII character."""
        # The fuzzer generated an octal tab (\011 -> \t)
        malicious_webhook = "click\t_hacked_control_char"

        # We don't need a mock transport here because the URL builder runs
        # and validates before the request ever touches the network.
        async with AsyncClient(auth=("api", "test-key")) as client:
            # The SDK MUST raise its own internal ValueError before httpx crashes
            with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
                await client.domains_webhooks.get(
                    domain="example.com", webhook_name=malicious_webhook
                )

    def test_domains_handler_path_traversal_prevention(self) -> None:
        """Ensure domain and webhook names are strictly sanitized in domains (CWE-20/22)."""
        client = Client(auth=("api", "key-123"))

        # Fuzzer-discovered payload containing Horizontal Tab (\x09) and prototype pollution
        malicious_payload = "OwwwyyyrepOww\x091www__proto__"

        # The SDK should fail-closed and catch the control character before it hits the HTTP layer
        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            client.domains_webhooks.get(
                domain=malicious_payload, webhook_name=malicious_payload
            )

    @pytest.mark.asyncio
    async def test_regression_cve_22_unhandled_path_parameter(self) -> None:
        """
        Proves that dynamic path parameters (like list_id or ip)
        are bypassing sanitize_path_segment() in the routing handlers.
        """
        # This exact combination creates the 31-character offset seen in the fuzzer crash
        api_url = "https://api.mailgun.net"
        malicious_ip = "\t_hacked_control_char"

        async with AsyncClient(auth=("api", "key"), api_url=api_url) as client:
            with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
                # The fuzzer did this dynamically via **kwargs
                await client.ips.delete(**{"ip": malicious_ip})

    @pytest.mark.asyncio
    async def test_regression_tags_domain_sanitization(self) -> None:
        """
        Regression Test for Differential Fuzzer Crash:
        Ensures that the 'domain' parameter in the tags handler is routed
        through sanitize_path_segment() to prevent InvalidURL crashes.
        """
        # The payload discovered by the fuzzer containing carriage returns, newlines, and tabs
        malicious_domain = "QQstw;;;%;%\rli\n  W.#\t;;;"

        async with AsyncClient(
            auth=("api", "key"), api_url="https://api.mailgun.net/v3"
        ) as client:
            # The SDK MUST intercept the control characters and fail-closed
            with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
                await client.tags.delete(domain=malicious_domain, tag_name="test-tag")

            with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
                # Triggering the "domains" fast-path
                await client.domains.get(domain=malicious_domain)

            with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
                await client.templates.get(
                    domain=malicious_domain, template_name="welcome-email"
                )

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "../",
            "/..",
            "1%2E%2E%2F",  # The specific payload found by the fuzzer
            "%2e%2e%2f",  # Lowercase variant
            "1../",
            "../../etc/passwd",
        ],
    )
    def test_sanitize_path_segment_prevents_traversal(
        self, malicious_input: str
    ) -> None:
        """
        Regression test for path traversal vulnerabilities.
        Ensures that encoded and raw traversal attempts are either
        stripped or raise a ValueError (fail-closed).
        """
        try:
            sanitized = SecurityGuard.sanitize_path_segment(malicious_input)

            # Invariant: The result must be clean
            assert ".." not in sanitized, f"Traversal sequence '..' found in {sanitized}"
            assert "/" not in sanitized, f"Path separator '/' found in {sanitized}"

        except ValueError:
            # If the function is designed to raise on violation, this is a pass
            pass

    def test_suppressions_handler_path_traversal_prevention(self) -> None:
        """Ensure domain parameters are properly sanitized in suppression endpoints."""
        client = Client(auth=("api", "key-123"))

        # Fuzzer-discovered payload containing Vertical Tab (\x0b) and SQLi/XSS chars
        malicious_domain = "\x0b<'#gt\x09<OR' =t#'IcIIIsxxx"

        # The SDK should fail-closed and catch the control character before it hits HTTP layer
        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            client.unsubscribes.delete(domain=malicious_domain)

        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            client.bounces.get(domain=malicious_domain)


class TestBuilderSecurityRegression:
    def test_add_custom_header_rejects_control_characters(self) -> None:
        """
        Regression test for CWE-20/CWE-113: Block Header Injection.
        Validates the fuzzer-discovered payload containing the \\x08 Backspace char.
        """
        builder = MailgunMessageBuilder("test@domain.com")

        # 1. Test the exact fuzzer artifact (Backspace character)
        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            builder.add_custom_header("ains\x08o", "safe_value")

        # 2. Test standard CRLF Header Injection
        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            builder.add_custom_header("X-Custom", "safe\r\nBcc: evil@hacker.com")

    def test_set_subject_rejects_control_characters(self) -> None:
        """Ensure subject lines cannot be used for MIME boundary manipulation."""
        builder = MailgunMessageBuilder("test@domain.com")

        with pytest.raises(ValueError, match=r"Security Alert \(CWE-20\)"):
            builder.set_subject("Monthly Report\nContent-Type: text/html")

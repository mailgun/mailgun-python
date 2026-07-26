import pytest

from mailgun.security import IdempotencyGuard, SpamGuard

class TestIdempotencyGuard:
    """Verifies deterministic SHA-256 fingerprinting for Exactly-Once Delivery."""

    def test_generate_key_creates_consistent_hash(self) -> None:
        """Ensure the same payload produces the exact same 64-character SHA-256 hash."""
        domain = "test.com"
        payload = {"to": "user@test.com", "subject": "Hello", "text": "Body"}

        key1 = IdempotencyGuard.generate_key(domain, payload)
        key2 = IdempotencyGuard.generate_key(domain, payload)

        assert key1 == key2
        assert len(key1) == 64

    def test_generate_key_ignores_volatile_options(self) -> None:
        """Coverage: Ensure non-core keys (like o:tracking) do not alter the content fingerprint."""
        domain = "test.com"
        payload_1 = {"to": "user@test.com", "subject": "Hello", "o:tracking": "yes"}
        payload_2 = {"to": "user@test.com", "subject": "Hello", "o:tracking": "no"}

        assert IdempotencyGuard.generate_key(domain, payload_1) == IdempotencyGuard.generate_key(domain, payload_2)

    def test_idempotency_chunked_stream(self) -> None:
        """Hits the hasattr(file_data, 'read') BytesIO chunking branch."""
        import io
        stream = io.BytesIO(b"Secure binary attachment data")
        key = IdempotencyGuard.generate_key("test.com", {}, files=[("report.pdf", stream)])

        assert len(key) == 64
        assert stream.tell() == 0  # Proves the pointer was rewound


class TestSpamGuard:
    """Verifies the Pre-Flight Static HTML analyzer fails correctly."""

    def test_analyze_html_penalizes_scripts(self) -> None:
        """CWE-79 Mitigation: Ensure scripts lower safety scores dramatically."""
        bad_html = "<html><body><script>alert('spam');</script></body></html>"
        result = SpamGuard.check_html(bad_html)

        assert result["is_safe"] is False
        assert result["score"] < 100.0

    def test_analyze_html_flags_missing_alt_attributes(self) -> None:
        """Deliverability check: Ensure missing alt tags trigger a warning penalty."""
        html_without_alt = "<html><body><img src='tracker.png'></body></html>"
        result = SpamGuard.check_html(html_without_alt)

        assert any("Missing 'alt' attributes" in issue for issue in result["issues"])

    def test_spam_guard_absolute_memory_limit(self) -> None:
        """Hits the > 5MB ValueError exception branch."""
        massive_payload = "a" * (SpamGuard.MAX_HTML_SIZE + 10)
        with pytest.raises(ValueError, match="Payload exceeds absolute safety limits"):
            SpamGuard.check_html(massive_payload)

    def test_spam_guard_parser_exception(self) -> None:
        """Hits the try/except block around parser.feed()."""
        with pytest.MonkeyPatch.context() as m:
            m.setattr("mailgun.security._SpamGuardParser.feed", lambda self, data: (_ for _ in ()).throw(RuntimeError("Simulated Parsing Crash")))
            report = SpamGuard.check_html("<html>Broken</html>")
            assert report["is_safe"] is False
            assert "Fatal HTML parsing error" in report["issues"][0]

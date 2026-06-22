import pytest
from unittest.mock import MagicMock, patch

from mailgun.config import Config
from mailgun.security import SecurityGuard


class TestEnterpriseAuditHooks:
    """Verify PEP 578 Enterprise Security Audit Hooks (Zero-Trust Telemetry)."""

    @patch("sys.audit")
    def test_audit_hook_emits_on_control_characters(
        self, mock_audit: MagicMock
    ) -> None:
        """Ensure control characters (CWE-20) trigger an audit event before crashing."""
        bad_input = "payload\x00hidden"

        with pytest.raises(ValueError, match="Security Alert \\(CWE-20\\)"):
            SecurityGuard.validate_no_control_characters(
                bad_input, context="PayloadField"
            )

        # Verify the SecOps team receives the context of the attack
        mock_audit.assert_called_once_with(
            "mailgun.security.control_characters", "PayloadField"
        )

    @patch("sys.audit")
    def test_audit_hook_emits_on_crlf_header_injection(
        self, mock_audit: MagicMock
    ) -> None:
        """Ensure CRLF injections (CWE-113) trigger an audit event before crashing."""
        bad_headers = {"X-Custom": "value\nInjected-Header: bad"}

        with pytest.raises(ValueError, match="CRLF injection detected"):
            SecurityGuard.sanitize_headers(bad_headers)

        # Verify the exact telemetry event was broadcasted to the runtime
        mock_audit.assert_called_once_with(
            "mailgun.security.header_injection", "X-Custom"
        )

    @patch("sys.audit")
    def test_audit_hook_emits_on_ssrf_attempt(self, mock_audit: MagicMock) -> None:
        """Ensure untrusted domains (CWE-918) trigger an SSRF audit event."""
        untrusted_url = "https://evil-phishing-domain.com/v3/messages"

        with pytest.raises(ValueError, match="Security Alert \\(CWE-918\\)"):
            SecurityGuard.validate_mailgun_url(untrusted_url)

        # Verify the exact malicious URL is sent to the audit log
        mock_audit.assert_called_once_with(
            "mailgun.security.ssrf_attempt", untrusted_url
        )

    @patch("sys.addaudithook")
    def test_enable_security_audit_registers_hook(
        self, mock_addaudithook: MagicMock
    ) -> None:
        """Ensure the opt-in security audit method successfully binds to the OS runtime."""
        # Call the opt-in method
        Config.enable_security_audit()

        # Verify the SDK successfully passed the listener to the Python interpreter
        mock_addaudithook.assert_called_once()

        # Verify the registered hook is a callable
        registered_hook = mock_addaudithook.call_args[0][0]
        assert callable(registered_hook)

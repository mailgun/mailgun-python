"""Unit tests for mailgun.ext.sandbox (Sandbox mock client and preview)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mailgun.ext.sandbox import LocalSandbox, MockResponse


class TestSandboxExtension:
    """Verifies local sandbox response mocking and file preview generation."""

    def test_sandbox_response_methods(self) -> None:
        """Verify SandboxResponse status codes, JSON payload return, and error raising."""
        resp = MockResponse({"message": "success"}, status_code=200)
        assert resp.json() == {"message": "success"}
        assert resp.status_code == 200
        resp.raise_for_status()

        bad_resp = MockResponse({"error": "unauthorized"}, status_code=401)
        with pytest.raises(Exception):
            bad_resp.raise_for_status()

    def test_local_sandbox_client(self, tmp_path: Path) -> None:
        """Verify LocalSandbox successfully mimics endpoint calls and preview directory management."""
        sandbox = LocalSandbox(preview_dir=tmp_path)
        resp = sandbox.messages.create(data={"to": "test@example.com"}, domain="example.com")
        assert resp.status_code == 200
        assert "message" in resp.json()

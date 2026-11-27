"""Tests for PEP 562 lazy top-level exports in mailgun.__init__."""

from __future__ import annotations

import subprocess
import sys

import pytest

import mailgun


def test_import_mailgun_does_not_eagerly_load_http_stack() -> None:
    code = (
        "import sys, mailgun; "
        "loaded = [m for m in ('mailgun.client', 'mailgun.endpoints', 'mailgun.builders', 'requests', 'httpx2') if m in sys.modules]; "
        "assert not loaded, f'Eagerly loaded: {loaded}'"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert res.returncode == 0, res.stderr


def test_lazy_exports_resolve_and_cache() -> None:
    for name in mailgun.__all__:
        val = getattr(mailgun, name)
        assert val is not None
        assert name in mailgun.__dict__


def test_lazy_submodules_resolve() -> None:
    for sub in ("builders", "client", "config", "endpoints", "routes", "security", "types"):
        mod = getattr(mailgun, sub)
        assert mod.__name__ == f"mailgun.{sub}"


def test_dir_and_unknown_attr() -> None:
    exported = dir(mailgun)
    for name in mailgun.__all__:
        assert name in exported
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent_xyz'"):
        _ = mailgun.nonexistent_xyz

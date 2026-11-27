"""Tests for PEP 484 (.pyi) stubs and py.typed marker."""

from __future__ import annotations

from pathlib import Path

from scripts.check_stubs import check_or_write_stubs


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "mailgun"


def test_py_typed_and_stubs_exist() -> None:
    """Verify py.typed marker and generated .pyi stub files exist."""
    assert (PACKAGE_DIR / "py.typed").is_file()
    assert (PACKAGE_DIR / "client.pyi").is_file()
    assert (PACKAGE_DIR / "endpoints.pyi").is_file()


def test_stubs_are_synchronized() -> None:
    """Verify tracked .pyi stubs match deterministic AST generation."""
    assert check_or_write_stubs(PACKAGE_DIR, write=False) == []

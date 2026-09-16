#!/usr/bin/env python3
"""Atheris target for Stateful Endpoint execution, full CRUDL transitions, and ID corruption."""

import contextlib
import logging
import sys
from unittest.mock import MagicMock, patch

import atheris


with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.endpoints import Endpoint
    from mailgun.handlers.error_handler import ApiError

_DEVNULL = sys.stderr
logging.disable(logging.CRITICAL)

_TARGET_ENDPOINTS = [
    "addressvalidate",
    "bounces",
    "domains",
    "ippools",
    "mailinglists",
    "messages",
    "routes",
    "stats",
    "tags",
    "users",
    "webhooks",
]


def _generate_fuzzed_id(fdp: atheris.FuzzedDataProvider) -> str:
    """Produce benign IDs, traversal attacks, unicode variants, and delimiters."""
    choice = fdp.ConsumeIntInRange(0, 4)
    if choice == 0:
        return fdp.ConsumeUnicodeNoSurrogates(12)
    if choice == 1:
        # Path traversal & delimiter injection
        prefix = fdp.PickValueInList(["../", "../../", "%2e%2e%2f", "/", "\\"])
        return f"{prefix}{fdp.ConsumeUnicodeNoSurrogates(8)}"
    if choice == 2:
        # URL encoding and special characters
        return fdp.PickValueInList(
            ["test@example.com", "tag:special", "id#123", "id?filter=1", "id%20space", ""]
        )
    if choice == 3:
        # Sub-resource path representation
        return f"{fdp.ConsumeUnicodeNoSurrogates(6)}/{fdp.ConsumeUnicodeNoSurrogates(6)}"
    return str(fdp.ConsumeInt(100000))


def TestOneInput(data: bytes) -> None:
    if len(data) < 24:
        return

    fdp = atheris.FuzzedDataProvider(data)
    active_ids: list[str] = []

    try:
        client = Client(auth=("api", "test-key"))

        mock_resp = MagicMock(
            status_code=200,
            json=lambda: {"items": [], "total_count": 0, "message": "success"},
            text='{"items": [], "total_count": 0, "message": "success"}',
        )

        with patch.object(client, "api_call", return_value=mock_resp):
            ep_name = fdp.PickValueInList(_TARGET_ENDPOINTS)
            endpoint: Endpoint = getattr(client, ep_name)

            num_operations = fdp.ConsumeIntInRange(2, 20)

            with contextlib.redirect_stdout(_DEVNULL), contextlib.redirect_stderr(_DEVNULL):
                for _ in range(num_operations):
                    op = fdp.ConsumeIntInRange(0, 4)

                    if op == 0:
                        # CREATE
                        new_id = _generate_fuzzed_id(fdp)
                        if hasattr(endpoint, "create"):
                            endpoint.create(data={"id": new_id, "name": fdp.ConsumeUnicodeNoSurrogates(10)})
                        active_ids.append(new_id)

                    elif op == 1:
                        # GET
                        target_id = fdp.PickValueInList(active_ids) if (active_ids and fdp.ConsumeBool()) else _generate_fuzzed_id(fdp)
                        if hasattr(endpoint, "get"):
                            endpoint.get(domain=target_id)

                    elif op == 2:
                        # LIST / QUERY
                        if hasattr(endpoint, "list"):
                            endpoint.list(params={"limit": fdp.ConsumeIntInRange(-5, 100)})
                        elif hasattr(endpoint, "get"):
                            endpoint.get(params={"limit": fdp.ConsumeIntInRange(1, 20)})

                    elif op == 3 and active_ids:
                        # UPDATE
                        target_id = fdp.PickValueInList(active_ids)
                        if hasattr(endpoint, "update"):
                            endpoint.update(
                                domain=target_id,
                                data={"fuzz_key": fdp.ConsumeUnicodeNoSurrogates(12), "val": fdp.ConsumeInt(1000)},
                            )

                    elif op == 4 and active_ids:
                        # DELETE
                        target_id = fdp.PickValueInList(active_ids)
                        if hasattr(endpoint, "delete"):
                            endpoint.delete(domain=target_id)
                        active_ids.remove(target_id)

    except (
        ApiError,
        AttributeError,
        KeyError,
        TypeError,
        UnicodeEncodeError,
        UnicodeDecodeError,
        ValueError,
    ):
        pass
    except Exception as exc:
        raise RuntimeError(f"Unexpected crash in endpoint lifecycle harness: {type(exc).__name__}: {exc}") from exc


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

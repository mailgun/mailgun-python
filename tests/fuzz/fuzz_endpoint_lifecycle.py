#!/usr/bin/env python3
"""Atheris target for Stateful Endpoint execution manipulation."""

import contextlib
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import atheris

with atheris.instrument_imports():
    from mailgun.client import Client
    from mailgun.endpoints import Endpoint
    from mailgun.handlers.error_handler import ApiError


_DEVNULL = open(os.devnull, "w")

logging.disable(logging.CRITICAL)


def TestOneInput(data: bytes) -> None:
    if len(data) < 20:
        return

    fdp = atheris.FuzzedDataProvider(data)
    active_ids: list[str] = []  # Track state!

    try:
        client = Client(auth=("api", "test-key"))

        # FIX: Safely mock the method using patch.object to respect slots restrictions
        with patch.object(
            client,
            "api_call",
            return_value=MagicMock(status_code=200, json=lambda: {"items": []}, text='{"items": []}')
        ):
            ep_name = fdp.PickValueInList(
                [
                    "addressvalidate",
                    "bounces",
                    "domains",
                    "ippools",
                    "mailinglists",
                    "messages",
                    "stats",
                    "tags",
                    "users",
                    "webhooks",
                ]
            )
            endpoint: Endpoint = getattr(client, ep_name)

            num_operations = fdp.ConsumeIntInRange(1, 15)

            with contextlib.redirect_stdout(_DEVNULL), contextlib.redirect_stderr(_DEVNULL):
                for _ in range(num_operations):
                    op = fdp.ConsumeIntInRange(0, 3)

                    if op == 0:  # CREATE
                        new_id = fdp.ConsumeUnicodeNoSurrogates(10)
                        endpoint.create(data={"id": new_id})
                        active_ids.append(new_id)

                    elif op == 1 and active_ids:  # UPDATE (Only if we have an ID)
                        target_id = fdp.PickValueInList(active_ids)
                        endpoint.update(domain=target_id, data={"fuzz": fdp.ConsumeInt(8)})

                    elif op == 2 and active_ids:  # DELETE (Only if we have an ID)
                        target_id = fdp.PickValueInList(active_ids)
                        endpoint.delete(domain=target_id)
                        active_ids.remove(target_id)  # Accurately reflect deleted state

    except (
            ApiError,
            AttributeError,
            KeyError,
            TypeError,
            UnicodeEncodeError,
            ValueError,
    ):
        # Expected during fuzzing: keep exploring inputs without failing the harness.
        pass


if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

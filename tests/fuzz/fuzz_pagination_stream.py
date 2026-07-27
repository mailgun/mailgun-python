#!/usr/bin/env python3
"""Fuzz test for Pagination Cursor Type-Casting & URL Parsing safety."""
import sys
from unittest.mock import patch

import atheris


with atheris.instrument_imports():
    from mailgun.client import Endpoint

def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    class MockPaginationResponse:
        def raise_for_status(self) -> None: pass
        def json(self) -> dict:
            # Fuzz the next URL parameters with extreme strings
            limit_val = fdp.ConsumeUnicodeNoSurrogates(32)
            asc_val = fdp.ConsumeUnicodeNoSurrogates(8)
            fuzzed_url = f"https://api.mailgun.net/v3/events?limit={limit_val}&ascending={asc_val}"

            return {"items": [{"id": 1}], "paging": {"next": fuzzed_url}}

    ep = Endpoint(url={"base": "http://test", "keys": []}, headers={}, auth=None)

    with patch.object(Endpoint, "get", return_value=MockPaginationResponse()):
        try:
            # Inject initial valid types to trigger the type-drift protection
            filters = {"limit": 10, "ascending": True}
            gen = ep.stream(filters=filters)

            next(gen) # Fetch the first page
            next(gen) # Trigger fetching the second page using the fuzzed URL

        except (ValueError, TypeError):
            # Safe rejections - The SDK correctly caught the hostile payload
            pass
        except StopIteration:
            # Normal generator exhaustion
            pass

if __name__ == "__main__":
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

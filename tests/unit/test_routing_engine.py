"""Meta-tests to verify URL routing for all endpoints defined in routes.py."""

from __future__ import annotations

import unittest
import warnings
from unittest.mock import MagicMock, patch

from mailgun import routes
from mailgun.client import Client


class TestRoutingEngine(unittest.TestCase):
    """Dynamically test that the SDK supports every route in routes.py."""

    def setUp(self) -> None:
        """Initialize a dummy client for URL generation testing."""
        self.client = Client(auth=("api", "fake-api-key"))
        self.domain = "python.test.com"

    @patch("requests.Session.request")
    def test_all_endpoints_can_generate_urls(self, mock_request: MagicMock) -> None:
        """Verify that every endpoint mapped in routes.py can generate a URL without KeyError.

        This test iterates through all registered routes, suppresses expected
        DeprecationWarnings, and ensures the routing engine produces valid Mailgun URLs.
        """
        mock_request.return_value = MagicMock(status_code=200)

        # Collect every single route key from configuration
        all_endpoints = set(routes.EXACT_ROUTES.keys()) | set(routes.PREFIX_ROUTES.keys())

        failed_resolutions = []
        successful_urls = []

        # We use catch_warnings because we are testing deprecated routes on purpose.
        # This prevents the DeprecationWarning from polluting the pytest summary.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            for endpoint_name in all_endpoints:
                # 'resend_message' is a special handler that requires 'storage_url' kwarg
                if endpoint_name == "resend_message":
                    continue

                try:
                    # 1. Resolve the endpoint attribute
                    ep = getattr(self.client, endpoint_name)

                    # 2. Trigger URL generation via a mocked request (handles both account & domain levels)
                    ep.get(domain=self.domain)

                    # 3. Extract the actually requested URL from the Mock
                    # Requests uses .request internally, we capture the call arguments
                    _method, target_url = mock_request.call_args[0] if mock_request.call_args[0] else (None, mock_request.call_args[1].get("url"))

                    if not target_url:
                         target_url = mock_request.call_args[1].get("url")

                    # Verify the URL is formulated correctly
                    self.assertTrue(str(target_url).startswith("https://api.mailgun.net/"))
                    successful_urls.append(f"{endpoint_name} -> {target_url}")

                except Exception as e:
                    failed_resolutions.append(f"Route '{endpoint_name}' failed: {e}")

        # Assert that no endpoints failed to generate a URL
        self.assertEqual(
            len(failed_resolutions),
            0,
            f"URL generation failed for {len(failed_resolutions)} endpoints:\n"
            + "\n".join(failed_resolutions),
        )

        # Print summary in verbose mode (-s)
        if successful_urls:
            print(f"\n[ROUTING ENGINE] Successfully validated {len(successful_urls)} routes.")

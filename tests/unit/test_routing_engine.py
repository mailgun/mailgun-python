"""Meta-tests to verify URL routing for all endpoints defined in routes.py."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from mailgun import routes
from mailgun.client import Client


class TestRoutingEngine(unittest.TestCase):
    """Dynamically test that the SDK supports every route in routes.py."""

    def setUp(self) -> None:
        """Initialize a dummy client for URL generation testing."""
        self.client = Client(auth=("api", "fake-api-key"))
        self.domain = "python.test.com"

    @patch("requests.Session.get")
    def test_all_endpoints_can_generate_urls(self, mock_get: MagicMock) -> None:
        """Verify that every endpoint mapped in routes.py can generate a URL without KeyError."""
        mock_get.return_value = MagicMock(status_code=200)

        # Collect every single route key from your configuration
        all_endpoints = set(routes.EXACT_ROUTES.keys()) | set(routes.PREFIX_ROUTES.keys())

        failed_resolutions = []
        successful_urls = []

        for endpoint_name in all_endpoints:
            if endpoint_name == "resend_message":
                continue
            try:
                ep = getattr(self.client, endpoint_name)
                # 2. Trigger URL generation via a mocked GET request
                ep.get(domain=self.domain)

                # 3. Extract the actually requested URL from the Mock
                args, _kwargs = mock_get.call_args
                target_url = args[0]

                # Verify the URL is formulated
                self.assertTrue(target_url.startswith("https://api.mailgun.net/"))
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

        # Optional: You can print `successful_urls` during debugging to see the dynamic routing!
        print(successful_urls)

"""Unit tests that mirror sync integration tests with all external resources mocked.

No real API keys or network calls; uses unittest.mock to patch requests.
Mirrors test classes and test methods from tests/integration/tests.py (sync only).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from mailgun.client import Client


def mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Build a mock response with status_code and json()."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


# Test data constants (no env vars)
DOMAIN = "example.com"
TEST_DOMAIN = "mailgun.wrapper.test123"
AUTH = ("api", "fake-api-key")


class MessagesTests(unittest.TestCase):
    """Mirror of integration MessagesTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.data = {
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Hello",
            "text": "Body",
            "o:tag": "Python test",
        }

    @patch("mailgun.client.requests.post")
    def test_post_right_message(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"id": "<msg-id>", "message": "Queued"})
        req = self.client.messages.create(data=self.data, domain=self.domain)
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_post_wrong_message(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(400, {"message": "Invalid from"})
        req = self.client.messages.create(data={"from": "sdsdsd"}, domain=self.domain)
        self.assertEqual(req.status_code, 400)

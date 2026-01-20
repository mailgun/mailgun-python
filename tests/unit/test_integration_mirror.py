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


class DomainTests(unittest.TestCase):
    """Mirror of integration DomainTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.test_domain = TEST_DOMAIN
        self.post_domain_data = {"name": self.test_domain}
        self.put_domain_data = {"spam_action": "disabled"}
        self.post_domain_creds = {
            "login": f"alice_bob@{self.domain}",
            "password": "test_new_creds123",
        }
        self.put_domain_creds = {"password": "test_new_creds"}
        self.put_domain_connections_data = {"require_tls": "false", "skip_verification": "false"}
        self.put_domain_tracking_data = {"active": "yes", "skip_verification": "false"}
        self.put_domain_unsubscribe_data = {
            "active": "yes",
            "html_footer": "\n<br>\n<p><a href=\"%unsubscribe_url%\">UnSuBsCrIbE</a></p>\n",
            "text_footer": "\n\nTo unsubscribe here click: <%unsubscribe_url%>\n\n",
        }
        self.put_domain_dkim_authority_data = {"self": "false"}
        self.put_domain_webprefix_data = {"web_prefix": "python"}
        self.put_dkim_selector_data = {"dkim_selector": "s"}

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_post_domain(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "ok"})
        m_post.return_value = mock_response(
            200, {"message": "Domain DNS records have been created"}
        )
        request = self.client.domains.create(data=self.post_domain_data)
        self.assertEqual(request.status_code, 200)
        self.assertIn("Domain DNS records have been created", request.json()["message"])

    @patch("mailgun.client.requests.post")
    def test_post_domain_creds(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Created"})
        request = self.client.domains_credentials.create(
            domain=self.domain, data=self.post_domain_creds
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    @patch("mailgun.client.requests.put")
    def test_update_simple_domain(
        self, m_put: MagicMock, m_post: MagicMock, m_delete: MagicMock
    ) -> None:
        m_delete.return_value = mock_response(200)
        m_post.return_value = mock_response(200, {"domain": {}})
        m_put.return_value = mock_response(200, {"message": "Domain has been updated"})
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains.put(
            data={"spam_action": "disabled"}, domain=self.post_domain_data["name"]
        )
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.json()["message"], "Domain has been updated")

    @patch("mailgun.client.requests.post")
    @patch("mailgun.client.requests.put")
    def test_put_domain_creds(self, m_put: MagicMock, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Created"})
        m_put.return_value = mock_response(200, {"message": "Updated"})
        self.client.domains_credentials.create(
            domain=self.domain, data=self.post_domain_creds
        )
        request = self.client.domains_credentials.put(
            domain=self.domain, data=self.put_domain_creds, login="alice_bob"
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.post")
    @patch("mailgun.client.requests.put")
    def test_put_mailboxes_credentials(self, m_put: MagicMock, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_put.return_value = mock_response(
            200,
            {
                "message": "Password changed",
                "note": "",
                "credentials": {f"alice_bob@{self.domain}": {}},
            },
        )
        self.client.domains_credentials.create(
            domain=self.domain, data=self.post_domain_creds
        )
        req = self.client.mailboxes.put(
            domain=self.domain, login=f"alice_bob@{self.domain}"
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("Password changed", req.json()["message"])

    @patch("mailgun.client.requests.get")
    def test_get_domain_list(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.domainlist.get()
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    def test_get_smtp_creds(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        request = self.client.domains_credentials.get(domain=self.domain)
        self.assertEqual(request.status_code, 200)
        self.assertIn("items", request.json())

    @patch("mailgun.client.requests.get")
    def test_get_sending_queues(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"scheduled": [], "retry": []})
        request = self.client.domains_sendingqueues.get(domain=self.test_domain)
        self.assertEqual(request.status_code, 200)
        self.assertIn("scheduled", request.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_single_domain(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_get.return_value = mock_response(200, {"domain": {"name": self.test_domain}})
        self.client.domains.create(data=self.post_domain_data)
        req = self.client.domains.get(domain_name=self.post_domain_data["name"])
        self.assertEqual(req.status_code, 200)
        self.assertIn("domain", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_verify_domain(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_put.return_value = mock_response(200, {"domain": {"state": "verified"}})
        self.client.domains.create(data=self.post_domain_data)
        req = self.client.domains.put(domain=self.post_domain_data["name"], verify=True)
        self.assertEqual(req.status_code, 200)
        self.assertIn("domain", req.json())

    @patch("mailgun.client.requests.put")
    def test_put_domain_connections(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        request = self.client.domains_connection.put(
            domain=self.domain, data=self.put_domain_connections_data
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    def test_put_domain_tracking_open(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        request = self.client.domains_tracking_open.put(
            domain=self.domain, data=self.put_domain_tracking_data
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    def test_put_domain_tracking_click(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        request = self.client.domains_tracking_click.put(
            domain=self.domain, data=self.put_domain_tracking_data
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    def test_put_domain_unsubscribe(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        request = self.client.domains_tracking_unsubscribe.put(
            domain=self.domain, data=self.put_domain_unsubscribe_data
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_put_dkim_authority(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_put.return_value = mock_response(200, {"message": "Updated"})
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_dkimauthority.put(
            domain=self.test_domain, data=self.put_domain_dkim_authority_data
        )
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_put_webprefix(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_put.return_value = mock_response(200, {"message": "Updated"})
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_webprefix.put(
            domain=self.test_domain, data=self.put_domain_webprefix_data
        )
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    def test_put_dkim_selector(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        request = self.client.domains_dkimselector.put(
            domain=self.domain, data=self.put_dkim_selector_data
        )
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.get")
    def test_get_dkim_keys(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {
                "items": [
                    {
                        "signing_domain": "python.test.domain5",
                        "selector": "smtp",
                        "dns_record": {},
                    }
                ],
                "paging": {},
            },
        )
        data = {
            "page": "string",
            "limit": "0",
            "signing_domain": "python.test.domain5",
            "selector": "smtp",
        }
        req = self.client.dkim_keys.get(data=data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())
        self.assertIn("paging", req.json())

    @patch("mailgun.client.requests.delete")
    def test_delete_dkim_keys(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "success"})
        query = {"signing_domain": "python.test.domain5", "selector": "smtp"}
        req = self.client.dkim_keys.delete(filters=query)
        self.assertEqual(req.status_code, 200)
        self.assertIn("success", req.json()["message"])

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_domain_creds(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_delete.return_value = mock_response(200)
        self.client.domains_credentials.create(
            domain=self.domain, data=self.post_domain_creds
        )
        request = self.client.domains_credentials.delete(
            domain=self.domain, login="alice_bob"
        )
        self.assertEqual(request.status_code, 200)

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_all_domain_credentials(
        self, m_post: MagicMock, m_delete: MagicMock
    ) -> None:
        m_post.return_value = mock_response(200)
        m_delete.return_value = mock_response(
            200, {"message": "All domain credentials have been deleted"}
        )
        self.client.domains_credentials.create(
            domain=self.domain, data=self.post_domain_creds
        )
        request = self.client.domains_credentials.delete(domain=self.domain)
        self.assertEqual(request.status_code, 200)
        self.assertIn(
            request.json()["message"], "All domain credentials have been deleted"
        )

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_domain(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_delete.return_value = mock_response(
            200, {"message": "Domain will be deleted in the background"}
        )
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains.delete(domain=self.test_domain)
        self.assertEqual(
            request.json()["message"], "Domain will be deleted in the background"
        )
        self.assertEqual(request.status_code, 200)


class IpTests(unittest.TestCase):
    """Mirror of integration IpTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.ip_data = {"ip": "1.2.3.4"}

    @patch("mailgun.client.requests.get")
    def test_get_ip_from_domain(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.ips.get(domain=self.domain, params={"dedicated": "true"})
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_ip_by_address(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response(200)
        m_get.return_value = mock_response(200, {"ip": self.ip_data["ip"]})
        self.client.domains_ips.create(domain=self.domain, data=self.ip_data)
        req = self.client.ips.get(domain=self.domain, ip=self.ip_data["ip"])
        self.assertIn("ip", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_create_ip(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "success"})
        request = self.client.domains_ips.create(domain=self.domain, data=self.ip_data)
        self.assertEqual("success", request.json()["message"])
        self.assertEqual(request.status_code, 200)

    @patch("mailgun.client.requests.delete")
    def test_delete_ip(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "success"})
        request = self.client.domains_ips.delete(
            domain=self.domain, ip=self.ip_data["ip"]
        )
        self.assertEqual("success", request.json()["message"])
        self.assertEqual(request.status_code, 200)


class IpPoolsTests(unittest.TestCase):
    """Mirror of integration IpPoolsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.data = {"name": "test_pool", "description": "Test", "add_ip": "1.2.3.4"}
        self.patch_data = {"name": "test_pool1", "description": "Test1"}

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_ippools(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"pool_id": "pid"})
        m_get.return_value = mock_response(200, {"ip_pools": []})
        self.client.ippools.create(domain=self.domain, data=self.data)
        req = self.client.ippools.get(domain=self.domain)
        self.assertIn("ip_pools", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.patch")
    @patch("mailgun.client.requests.post")
    def test_patch_ippool(self, m_post: MagicMock, m_patch: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"pool_id": "pid123"})
        m_patch.return_value = mock_response(200, {"message": "success"})
        self.client.ippools.create(domain=self.domain, data=self.data)
        req = self.client.ippools.patch(
            domain=self.domain, data=self.patch_data, pool_id="pid123"
        )
        self.assertEqual("success", req.json()["message"])
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_link_domain_ippool(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Linked"})
        req = self.client.domains_ips.create(
            domain=self.domain, data={"pool_id": "pid123"}
        )
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_ippool(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"pool_id": "pid123"})
        m_delete.return_value = mock_response(200, {"message": "started"})
        self.client.ippools.create(domain=self.domain, data=self.data)
        req_del = self.client.ippools.delete(
            domain=self.domain, pool_id="pid123"
        )
        self.assertEqual("started", req_del.json()["message"])


class EventsTests(unittest.TestCase):
    """Mirror of integration EventsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.params = {"event": "rejected"}

    @patch("mailgun.client.requests.get")
    def test_events_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.events.get(domain=self.domain)
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.get")
    def test_event_params(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.events.get(domain=self.domain, filters=self.params)
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

"""Unit tests that mirror sync integration tests with all external resources mocked.

No real API keys or network calls; uses unittest.mock to patch requests.
Mirrors test classes and test methods from tests/integration/tests.py (sync only).
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from mailgun.client import Client


def mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Build a mock response with status_code and json()."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}

    resp.text = json.dumps(json_data) if json_data is not None else ""

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
            "password": "test_new_creds123", # pragma: allowlist secret
        }
        self.put_domain_creds = {"password": "test_new_creds"} # pragma: allowlist secret
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
        m_delete.return_value = mock_response()
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
        m_post.return_value = mock_response()
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
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"domain": {"name": self.test_domain}})
        self.client.domains.create(data=self.post_domain_data)
        req = self.client.domains.get(domain_name=self.post_domain_data["name"])
        self.assertEqual(req.status_code, 200)
        self.assertIn("domain", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_verify_domain(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response()
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
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"message": "Updated"})
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_dkimauthority.put(
            domain=self.test_domain, data=self.put_domain_dkim_authority_data
        )
        self.assertIn("message", request.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_put_webprefix(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response()
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
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response()
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
        m_post.return_value = mock_response()
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
        m_post.return_value = mock_response()
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
        m_post.return_value = mock_response()
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


class TagsTests(unittest.TestCase):
    """Mirror of integration TagsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.data = {"description": "Tests running"}
        self.put_tags_data = {"description": "Python testtt"}
        self.stats_params = {"event": "accepted"}
        self.tag_name = "Python test"

    @patch("mailgun.client.requests.get")
    def test_get_tags(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.tags.get(domain=self.domain)
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.get")
    def test_tag_get_by_name(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"tag": {"name": self.tag_name}})
        req = self.client.tags.get(domain=self.domain, tag_name=self.tag_name)
        self.assertIn("tag", req.json())
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.put")
    def test_tag_put(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        req = self.client.tags.put(
            domain=self.domain,
            tag_name=self.tag_name,
            data=self.put_tags_data,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_tags_stats_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"tag": {}})
        req = self.client.tags_stats.get(
            domain=self.domain,
            filters=self.stats_params,
            tag_name=self.tag_name,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("tag", req.json())

    @patch("mailgun.client.requests.get")
    def test_tags_stats_aggregate_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"tag": {}})
        req = self.client.tags_stats_aggregates_devices.get(
            domain=self.domain,
            filters=self.stats_params,
            tag_name=self.tag_name,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("tag", req.json())

    @patch("mailgun.client.requests.delete")
    def test_delete_tags(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.tags.delete(
            domain=self.domain, tag_name=self.tag_name
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class BouncesTests(unittest.TestCase):
    """Mirror of integration BouncesTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.bounces_data = {
            "address": "test30@gmail.com",
            "code": 550,
            "error": "Test error",
        }
        self.bounces_json_data = """[{
            "address": "test121@i.ua",
            "code": "550",
            "error": "Test error2312"
        }, {
            "address": "test122@gmail.com",
            "code": "550",
            "error": "Test error"
        }]"""

    @patch("mailgun.client.requests.get")
    def test_bounces_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.bounces.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.post")
    def test_bounces_create(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"address": self.bounces_data["address"]})
        req = self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_bounces_get_address(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"address": self.bounces_data["address"]})
        self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        req = self.client.bounces.get(
            domain=self.domain, bounce_address=self.bounces_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    @patch("mailgun.client.requests.post")
    def test_bounces_create_json(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        json_data = json.loads(self.bounces_json_data)
        for address in json_data:
            req = self.client.bounces.create(
                data=address,
                domain=self.domain,
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_bounces_delete_single(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        req = self.client.bounces.delete(
            domain=self.domain, bounce_address=self.bounces_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    def test_bounces_delete_all(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.bounces.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class UnsubscribesTests(unittest.TestCase):
    """Mirror of integration UnsubscribesTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.unsub_data = {"address": "test@gmail.com", "tag": "unsub_test_tag"}
        self.unsub_json_data = """[{"address": "test1@gmail.com", "tags": ["some tag"]},
            {"address": "test2@gmail.com", "code": ["*"]}, {"address": "test3@gmail.com"}]"""

    @patch("mailgun.client.requests.post")
    def test_unsub_create(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        req = self.client.unsubscribes.create(data=self.unsub_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_unsub_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.unsubscribes.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    def test_unsub_get_single(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"address": self.unsub_data["address"]})
        req = self.client.unsubscribes.get(
            domain=self.domain, unsubscribe_address=self.unsub_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    @patch("mailgun.client.requests.post")
    def test_unsub_create_multiple(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        json_data = json.loads(self.unsub_json_data)
        for address in json_data:
            req = self.client.unsubscribes.create(
                data=address,
                domain=self.domain,
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    def test_unsub_delete(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.unsubscribes.delete(
            domain=self.domain, unsubscribe_address=self.unsub_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    def test_unsub_delete_all(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.unsubscribes.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class ComplaintsTests(unittest.TestCase):
    """Mirror of integration ComplaintsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.compl_data = {"address": "test@gmail.com", "tag": "compl_test_tag"}
        self.compl_json_data = """[{"address": "test1@gmail.com", "tags": ["some tag"]},
            {"address": "test3@gmail.com"}]"""

    @patch("mailgun.client.requests.post")
    def test_compl_create(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        req = self.client.complaints.create(data=self.compl_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_get_single_complaint(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.complaints.get(data=self.compl_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    def test_compl_get_all(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.complaints.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_compl_get_single(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"address": self.compl_data["address"]})
        self.client.complaints.create(data=self.compl_data, domain=self.domain)
        req = self.client.complaints.get(
            domain=self.domain, complaint_address=self.compl_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    @patch("mailgun.client.requests.post")
    def test_compl_create_multiple(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        json_data = json.loads(self.compl_json_data)
        for address in json_data:
            req = self.client.complaints.create(
                data=address,
                domain=self.domain,
                headers={"Content-type": "application/json"},
            )
            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_compl_delete_single(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.complaints.delete(
            domain=self.domain, unsubscribe_address=self.compl_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    def test_compl_delete_all(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.complaints.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class WhiteListTests(unittest.TestCase):
    """Mirror of integration WhiteListTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.whitel_data = {"address": "test@gmail.com"}

    @patch("mailgun.client.requests.post")
    def test_whitel_create(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        req = self.client.whitelists.create(data=self.whitel_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_whitel_get_simple(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.whitelists.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.delete")
    def test_whitel_delete_simple(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.whitelists.delete(
            domain=self.domain, whitelist_address=self.whitel_data["address"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class RoutesTests(unittest.TestCase):
    """Mirror of integration RoutesTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.sender = "sender@example.com"
        self.routes_data = {
            "priority": 0,
            "description": "Sample route",
            "expression": f"match_recipient('.*@{self.domain}')",
            "action": ["forward('http://myhost.com/messages/')", "stop()"],
        }
        self.routes_params = {"skip": 1, "limit": 1}
        self.routes_put_data = {"priority": 2}

    @patch("mailgun.client.requests.post")
    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.get")
    def test_routes_create(
        self, m_get: MagicMock, m_delete: MagicMock, m_post: MagicMock
    ) -> None:
        m_get.return_value = mock_response(200, {"items": [{"id": "rid"}]})
        m_delete.return_value = mock_response()
        m_post.return_value = mock_response(200, {"message": "Route created"})
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        if req1.json().get("items"):
            self.client.routes.delete(
                domain=self.domain, route_id=req1.json()["items"][0]["id"]
            )
        req = self.client.routes.create(domain=self.domain, data=self.routes_data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_routes_get_all(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.routes.get(domain=self.domain, filters=self.routes_params)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_route_by_id(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"route": {"id": "rid123"}})
        m_get.return_value = mock_response(200, {"route": {"id": "rid123"}})
        req_post = self.client.routes.create(
            domain=self.domain, data=self.routes_data
        )
        req = self.client.routes.get(
            domain=self.domain, route_id=req_post.json()["route"]["id"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("route", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_routes_put(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"route": {"id": "rid123"}})
        m_put.return_value = mock_response(200, {"message": "Updated"})
        req_post = self.client.routes.create(
            domain=self.domain, data=self.routes_data
        )
        req = self.client.routes.put(
            domain=self.domain,
            data=self.routes_put_data,
            route_id=req_post.json()["route"]["id"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_routes_delete(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"route": {"id": "rid123"}})
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req_post = self.client.routes.create(
            domain=self.domain, data=self.routes_data
        )
        req = self.client.routes.delete(
            domain=self.domain, route_id=req_post.json()["route"]["id"]
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.get")
    def test_get_routes_match(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {
                "route": {
                    "actions": [],
                    "created_at": "",
                    "description": "",
                    "expression": "",
                    "id": "r1",
                    "priority": 0,
                }
            },
        )
        query = {"address": self.sender}
        req = self.client.routes_match.get(domain=self.domain, filters=query)
        self.assertEqual(req.status_code, 200)
        self.assertIn("route", req.json())
        expected_keys = [
            "actions", "created_at", "description", "expression", "id", "priority"
        ]
        for key in expected_keys:
            self.assertIn(key, req.json()["route"])


class WebhooksTests(unittest.TestCase):
    """Mirror of integration WebhooksTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.webhooks_data = {"id": "clicked", "url": ["https://i.ua"]}
        self.webhooks_data_put = {"url": "https://twitter.com"}

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_webhooks_create(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Created"})
        m_delete.return_value = mock_response()
        req = self.client.domains_webhooks.create(
            domain=self.domain, data=self.webhooks_data
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    @patch("mailgun.client.requests.get")
    def test_webhooks_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"webhooks": {}})
        req = self.client.domains_webhooks.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("webhooks", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_webhook_put(self, m_post: MagicMock, m_put: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"message": "Updated"})
        m_delete.return_value = mock_response(200)

        self.client.domains_webhooks.create(
            domain=self.domain, data=self.webhooks_data
        )
        req = self.client.domains_webhooks_clicked.put(
            domain=self.domain, data=self.webhooks_data_put
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_webhook_get_simple(self, m_post: MagicMock, m_get: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"webhook": {}})
        m_delete.return_value = mock_response(200)

        self.client.domains_webhooks.create(
            domain=self.domain, data=self.webhooks_data
        )
        req = self.client.domains_webhooks_clicked.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("webhook", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_webhook_delete(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        self.client.domains_webhooks.create(
            domain=self.domain, data=self.webhooks_data
        )
        req = self.client.domains_webhooks_clicked.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class MailingListsTests(unittest.TestCase):
    """Mirror of integration MailingListsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.maillist_address = f"list@{self.domain}"
        self.mailing_lists_data = {
            "address": f"python_sdk@{self.domain}",
            "description": "Mailgun developers list",
        }
        self.mailing_lists_data_update = {"description": "Mailgun developers list 121212"}
        self.mailing_lists_members_data = {
            "subscribed": True,
            "address": "bar@example.com",
            "name": "Bob Bar",
            "description": "Developer",
            "vars": '{"age": 26}',
        }
        self.mailing_lists_members_put_data = {
            "subscribed": True,
            "address": "bar@example.com",
            "name": "Bob Bar",
            "description": "Developer",
            "vars": '{"age": 28}',
        }
        self.mailing_lists_members_data_mult = {
            "upsert": True,
            "members": '[{"address": "alice@example.com"}, {"address": "bob@example.com"}]',
        }

    @patch("mailgun.client.requests.get")
    def test_maillist_pages_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.lists_pages.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    def test_maillist_lists_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"list": {}})
        req = self.client.lists.get(
            domain=self.domain, address=self.maillist_address
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    @patch("mailgun.client.requests.post")
    def test_maillist_lists_create(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"list": {}})
        req = self.client.lists.create(
            domain=self.domain, data=self.mailing_lists_data
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_maillists_lists_put(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"list": {}})
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)
        req = self.client.lists.put(
            domain=self.domain,
            data=self.mailing_lists_data_update,
            address=f"python_sdk@{self.domain}",
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_maillists_lists_delete(
        self, m_post: MagicMock, m_delete: MagicMock
    ) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response()
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)
        req = self.client.lists.delete(
            domain=self.domain, address=f"python_sdk@{self.domain}"
        )
        self.assertEqual(req.status_code, 200)
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)

    @patch("mailgun.client.requests.get")
    def test_maillists_lists_members_pages_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.lists_members_pages.get(
            domain=self.domain, address=self.maillist_address
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.post")
    @patch("mailgun.client.requests.delete")
    def test_maillists_lists_members_create(
        self, m_delete: MagicMock, m_post: MagicMock
    ) -> None:
        m_delete.return_value = mock_response()
        m_post.return_value = mock_response(200, {"member": {}})
        req = self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("member", req.json())

    @patch("mailgun.client.requests.get")
    def test_maillists_lists_members_get(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"items": []})
        req = self.client.lists_members.get(
            domain=self.domain, address=self.maillist_address
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_maillists_lists_members_update(
        self, m_post: MagicMock, m_put: MagicMock
    ) -> None:
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"member": {}})
        self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data,
        )
        req = self.client.lists_members.put(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_put_data,
            member_address=self.mailing_lists_members_data["address"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("member", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_maillists_lists_members_delete(
        self, m_post: MagicMock, m_delete: MagicMock
    ) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response()
        self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data,
        )
        req = self.client.lists_members.delete(
            domain=self.domain,
            address=self.maillist_address,
            member_address=self.mailing_lists_members_data["address"],
        )
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_maillists_lists_members_create_mult(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"message": "Added"})
        req = self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data_mult,
            multiple=True,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class TemplatesTests(unittest.TestCase):
    """Mirror of integration TemplatesTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.post_template_data = {
            "name": "template.name20",
            "description": "template description",
            "template": "{{fname}} {{lname}}",
            "engine": "handlebars",
            "comment": "version comment",
        }
        self.put_template_data = {"description": "new template description"}
        self.post_template_version_data = {
            "tag": "v11",
            "template": "{{fname}} {{lname}}",
            "engine": "handlebars",
            "active": "no",
        }
        self.put_template_version_data = {
            "template": "{{fname}} {{lname}}",
            "comment": "Updated version comment",
            "active": "no",
        }
        self.put_template_version = "v11"

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_create_template(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response()
        m_post.return_value = mock_response(200, {"template": {}})
        self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
        )
        req = self.client.templates.create(
            data=self.post_template_data, domain=self.domain
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_template(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"template": {}})
        params = {"active": "yes"}
        req = self.client.templates.get(
            domain=self.domain,
            filters=params,
            template_name=self.post_template_data["name"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_put_template(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"template": {}})
        self.client.templates.create(
            data=self.post_template_data, domain=self.domain
        )
        req = self.client.templates.put(
            domain=self.domain,
            data=self.put_template_data,
            template_name=self.post_template_data["name"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_template(self, m_post: MagicMock, m_delete: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response()
        self.client.templates.create(
            data=self.post_template_data, domain=self.domain
        )
        req = self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
        )
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_post_version_template(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"template": {}})
        req = self.client.templates.create(
            data=self.post_template_version_data,
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.get")
    @patch("mailgun.client.requests.post")
    def test_get_version_template(self, m_post: MagicMock, m_get: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_get.return_value = mock_response(200, {"template": {}})
        req = self.client.templates.get(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.put")
    @patch("mailgun.client.requests.post")
    def test_put_version_template(self, m_post: MagicMock, m_put: MagicMock) -> None:
        m_post.return_value = mock_response()
        m_put.return_value = mock_response(200, {"template": {}})
        req = self.client.templates.put(
            domain=self.domain,
            data=self.put_template_version_data,
            template_name=self.post_template_data["name"],
            versions=True,
            tag=self.put_template_version,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.post")
    def test_delete_version_template(
        self, m_post: MagicMock, m_delete: MagicMock
    ) -> None:
        m_post.return_value = mock_response()
        m_delete.return_value = mock_response()
        self.client.templates.create(
            data=self.post_template_data, domain=self.domain
        )
        req = self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
            tag="v0",
        )
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.put")
    def test_update_template_version_copy(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(
            200,
            {
                "message": "version has been copied",
                "version": {"tag": "v3"},
                "template": {
                    "tag": "v3",
                    "template": "",
                    "engine": "handlebars",
                    "mjml": False,
                    "createdAt": "",
                    "comment": "",
                    "active": "no",
                    "id": "",
                    "headers": {},
                },
            },
        )
        data = {"comment": "An updated version comment"}
        req = self.client.templates.put(
            domain=self.domain,
            filters=data,
            template_name="template.name1",
            versions=True,
            tag="v2",
            copy=True,
            new_tag="v3",
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("version has been copied", req.json()["message"])


class MetricsTest(unittest.TestCase):
    """Mirror of integration MetricsTest with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        now = datetime.now()
        now_formatted = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        yesterday_formatted = (now - timedelta(days=1)).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        self.account_metrics_data = {
            "start": yesterday_formatted,
            "end": now_formatted,
            "resolution": "day",
            "duration": "1m",
            "dimensions": ["time"],
            "metrics": ["accepted_count", "delivered_count", "clicked_rate", "opened_rate"],
            "filter": {
                "AND": [
                    {
                        "attribute": "domain",
                        "comparator": "=",
                        "values": [{"label": self.domain, "value": self.domain}],
                    }
                ]
            },
            "include_subaccounts": True,
            "include_aggregates": True,
        }
        self.invalid_account_metrics_data = self.account_metrics_data | {
            "resolution": "century",
            "duration": "1c",
        }
        self.account_usage_metrics_data = {
            "start": yesterday_formatted,
            "end": now_formatted,
            "resolution": "day",
            "duration": "1m",
            "dimensions": ["time"],
            "metrics": ["accessibility_count", "processed_count"],
            "include_subaccounts": True,
            "include_aggregates": True,
        }
        self.invalid_account_usage_metrics_data = self.account_usage_metrics_data | {
            "resolution": "century",
        }

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_metrics(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(
            200,
            {
                "start": "",
                "end": "",
                "resolution": "day",
                "duration": "1m",
                "dimensions": [],
                "pagination": {},
                "items": [{"metrics": {"delivered_count": 0}, "dimensions": {}}],
                "aggregates": {},
            },
        )
        req = self.client.analytics_metrics.create(data=self.account_metrics_data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())
        self.assertIn("delivered_count", req.json()["items"][0]["metrics"])

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_metrics_invalid_data(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(
            400, {"message": "'resolution' attribute is invalid"}
        )
        req = self.client.analytics_metrics.create(
            data=self.invalid_account_metrics_data
        )
        self.assertEqual(req.status_code, 400)
        self.assertIn("'resolution' attribute is invalid", req.json()["message"])

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_metrics_invalid_url(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(404, {})
        req = self.client.analytics_metric.create(data=self.account_metrics_data)
        self.assertEqual(req.status_code, 404)

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_usage_metrics(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(
            200,
            {
                "start": "",
                "end": "",
                "resolution": "day",
                "duration": "1m",
                "dimensions": [],
                "pagination": {},
                "items": [{"metrics": {"email_validation_count": 0}, "dimensions": {}}],
                "aggregates": {},
            },
        )
        req = self.client.analytics_usage_metrics.create(
            data=self.account_usage_metrics_data
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("email_validation_count", req.json()["items"][0]["metrics"])

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_usage_metrics_invalid_data(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(
            400, {"message": "'resolution' attribute is invalid"}
        )
        req = self.client.analytics_usage_metrics.create(
            data=self.invalid_account_usage_metrics_data
        )
        self.assertEqual(req.status_code, 400)

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_usage_metrics_invalid_url(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(404, {})
        req = self.client.analytics_usage_metric.create(
            data=self.invalid_account_usage_metrics_data
        )
        self.assertEqual(req.status_code, 404)


class LogsTests(unittest.TestCase):
    """Mirror of integration LogsTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        now = datetime.now()
        now_formatted = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        yesterday_formatted = (now - timedelta(days=1)).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        self.account_logs_data = {
            "start": yesterday_formatted,
            "end": now_formatted,
            "filter": {
                "AND": [
                    {
                        "attribute": "domain",
                        "comparator": "=",
                        "values": [{"label": self.domain, "value": self.domain}],
                    }
                ]
            },
            "include_subaccounts": True,
            "pagination": {"sort": "timestamp:asc", "limit": 50},
        }
        self.invalid_account_logs_data = {
            "start": yesterday_formatted,
            "end": now_formatted,
            "filter": {
                "AND": [
                    {
                        "attribute": "test",
                        "comparator": "=",
                        "values": [{"label": "", "value": ""}],
                    }
                ]
            },
            "include_subaccounts": True,
            "pagination": {"sort": "timestamp:asc", "limit": 0},
        }

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_logs(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(
            200,
            {
                "start": "",
                "end": "",
                "pagination": {},
                "items": [{"event": "", "account": ""}],
                "aggregates": {},
            },
        )
        req = self.client.analytics_logs.create(data=self.account_logs_data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())
        self.assertIn("event", req.json()["items"][0])

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_logs_invalid_data(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(
            400,
            {"message": "'test' is not a valid filter predicate attribute"},
        )
        req = self.client.analytics_logs.create(
            data=self.invalid_account_logs_data
        )
        self.assertEqual(req.status_code, 400)
        self.assertIn(
            "'test' is not a valid filter predicate attribute",
            req.json()["message"],
        )

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_logs_invalid_url(
        self, m_post: MagicMock
    ) -> None:
        m_post.return_value = mock_response(404, {})
        req = self.client.analytics_log.create(data=self.account_logs_data)
        self.assertEqual(req.status_code, 404)


class TagsNewTests(unittest.TestCase):
    """Mirror of integration TagsNewTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.account_tags_data = {
            "pagination": {"sort": "lastseen:desc", "limit": 10},
            "include_subaccounts": True,
        }
        self.account_tag_info = '{"tag": "Python test", "description": "updated"}'
        self.account_tag_invalid_info = '{"tag": "test", "description": "updated"}'

    @patch("mailgun.client.requests.put")
    def test_update_account_tag(self, m_put: MagicMock) -> None:
        m_put.return_value = mock_response(200, {"message": "Updated"})
        req = self.client.analytics_tags.put(data=self.account_tag_info)
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_tags(self, m_post: MagicMock) -> None:
        """Post query to list account tags (integration uses .create with data)."""
        m_post.return_value = mock_response(
            200,
            {"pagination": {"sort": "lastseen:desc", "limit": 10}, "items": []},
        )
        req = self.client.analytics_tags.create(data=self.account_tags_data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("pagination", req.json())
        self.assertIn("items", req.json())
        self.assertIn("sort", req.json()["pagination"])
        self.assertIn("limit", req.json()["pagination"])

    @patch("mailgun.client.requests.post")
    def test_post_query_get_account_tags_with_incorrect_url(
        self, m_post: MagicMock
    ) -> None:
        """Invalid URL (analytics_tag singular) returns 404."""
        m_post.return_value = mock_response(404, {"error": "Not found"})
        req = self.client.analytics_tag.create(data=self.account_tags_data)
        self.assertEqual(req.status_code, 404)
        self.assertIn("error", req.json())

    @patch("mailgun.client.requests.delete")
    def test_delete_account_tag(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(200, {"message": "Deleted"})
        req = self.client.analytics_tags.delete(tag_name="Python test")
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.delete")
    def test_delete_account_nonexistent_tag(self, m_delete: MagicMock) -> None:
        m_delete.return_value = mock_response(404, {"message": "Not found"})
        req = self.client.analytics_tags.delete(tag_name="nonexistent")
        self.assertEqual(req.status_code, 404)

    @patch("mailgun.client.requests.get")
    def test_get_account_tag_limit_information(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(200, {"limits": {}})
        req = self.client.analytics_tags_limits.get()
        self.assertEqual(req.status_code, 200)


class BounceClassificationTests(unittest.TestCase):
    """Mirror of integration BounceClassificationTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN

    @patch("mailgun.client.requests.post")
    def test_post_list_statistic(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(200, {"items": []})
        data = {
            "dimensions": ["classification_id"],
            "start": "2024-01-01",
            "end": "2024-01-31",
        }
        req = self.client.analytics_bounce_classification_metrics.create(data=data)
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.post")
    def test_post_list_statistic_without_dimensions(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(400, {"message": "dimensions required"})
        data = {"start": "2024-01-01", "end": "2024-01-31"}
        req = self.client.analytics_bounce_classification_metrics.create(data=data)
        self.assertEqual(req.status_code, 400)

    @patch("mailgun.client.requests.post")
    def test_post_list_statistic_with_old_dates(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(
            400, {"message": "is out of permitted log retention"}
        )
        data = {
            "dimensions": ["classification_id"],
            "start": "2020-01-01",
            "end": "2020-01-31",
        }
        req = self.client.analytics_bounce_classification_metrics.create(data=data)
        self.assertEqual(req.status_code, 400)
        self.assertIn("message", req.json())

    @patch("mailgun.client.requests.post")
    def test_post_list_statistic_with_empty_payload(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(400, {"message": "Bad request"})
        req = self.client.analytics_bounce_classification_metrics.create(data={})
        self.assertEqual(req.status_code, 400)


class UsersTests(unittest.TestCase):
    """Mirror of integration UsersTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.client_with_secret_key = Client(auth=("api", "fake-secret"))
        self.domain = DOMAIN
        self.mailgun_email = "user@example.com"

    @patch("mailgun.client.requests.get")
    def test_get_users(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {
                "total": 1,
                "users": [
                    {
                        "account_id": "",
                        "activated": True,
                        "auth": {},
                        "email": self.mailgun_email,
                        "id": "uid",
                        "role": "admin",
                        "name": "",
                        "is_disabled": False,
                        "is_master": False,
                        "metadata": {},
                        "migration_status": "",
                        "email_details": {},
                        "github_user_id": "",
                        "opened_ip": "",
                        "password_updated_at": "",
                        "preferences": {},
                        "salesforce_user_id": "",
                        "tfa_active": False,
                        "tfa_created_at": "",
                        "tfa_enabled": False,
                    }
                ],
            },
        )
        query = {"role": "admin", "limit": "0", "skip": "0"}
        req = self.client.users.get(filters=query)
        self.assertEqual(req.status_code, 200)
        self.assertIn("users", req.json())
        self.assertIn("total", req.json())

    @patch("mailgun.client.requests.get")
    def test_own_user_details(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {
                "account_id": "",
                "activated": True,
                "auth": {},
                "email": self.mailgun_email,
                "id": "me",
                "role": "admin",
                "name": "",
                "is_disabled": False,
                "is_master": False,
                "metadata": {},
                "migration_status": "",
                "email_details": {},
                "github_user_id": "",
                "opened_ip": "",
                "password_updated_at": "",
                "preferences": {},
                "salesforce_user_id": "",
                "tfa_active": False,
                "tfa_created_at": "",
                "tfa_enabled": False,
            },
        )
        req = self.client_with_secret_key.users.get(user_id="me")
        self.assertEqual(req.status_code, 200)

    @patch("mailgun.client.requests.get")
    def test_get_user_details(self, m_get: MagicMock) -> None:
        user_obj = {
            "account_id": "",
            "activated": True,
            "auth": {},
            "email": self.mailgun_email,
            "id": "uid",
            "role": "admin",
            "name": "",
            "is_disabled": False,
            "is_master": False,
            "metadata": {},
            "migration_status": "",
            "email_details": {},
            "github_user_id": "",
            "opened_ip": "",
            "password_updated_at": "",
            "preferences": {},
            "salesforce_user_id": "",
            "tfa_active": False,
            "tfa_created_at": "",
            "tfa_enabled": False,
        }
        m_get.side_effect = [
            mock_response(200, {"users": [user_obj], "total": 1}),
            mock_response(200, user_obj),
        ]
        query = {"role": "admin", "limit": "0", "skip": "0"}
        req1 = self.client.users.get(filters=query)
        user_id = req1.json()["users"][0]["id"]
        req2 = self.client.users.get(user_id=user_id)
        self.assertEqual(req2.status_code, 200)

    @patch("mailgun.client.requests.get")
    def test_get_invalid_user_details(self, m_get: MagicMock) -> None:
        m_get.side_effect = [
            mock_response(200, {"users": [{"id": "uid", "email": self.mailgun_email}], "total": 1}),
            mock_response(404, {"message": "Not found"}),
        ]
        query = {"role": "admin", "limit": "0", "skip": "0"}
        req1 = self.client.users.get(filters=query)
        for user in req1.json()["users"]:
            if self.mailgun_email == user["email"]:
                req2 = self.client.users.get(user_id="xxxxxxx")
                self.assertEqual(req2.status_code, 404)
            break


class KeysTests(unittest.TestCase):
    """Mirror of integration KeysTests with mocked HTTP."""

    def setUp(self) -> None:
        self.client = Client(auth=AUTH)
        self.domain = DOMAIN
        self.mailgun_email = "user@example.com"
        self.role = "admin"
        self.user_id = "uid"
        self.user_name = "Test User"

    @patch("mailgun.client.requests.get")
    def test_get_keys(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {"total_count": 1, "items": [{"id": "key1", "requestor": self.mailgun_email}]},
        )
        query = {"domain_name": "python.test.domain5", "kind": "web"}
        req = self.client.keys.get(filters=query)
        self.assertEqual(req.status_code, 200)
        self.assertIn("total_count", req.json())
        self.assertIn("items", req.json())

    @patch("mailgun.client.requests.get")
    def test_get_keys_without_filtering_data(self, m_get: MagicMock) -> None:
        m_get.return_value = mock_response(
            200, {"items": [{"id": "k1", "description": "test"}]}
        )
        req = self.client.keys.get()
        self.assertEqual(req.status_code, 200)
        self.assertGreater(len(req.json()["items"]), 0)

    @patch("mailgun.client.requests.post")
    def test_post_keys(self, m_post: MagicMock) -> None:
        m_post.return_value = mock_response(
            200,
            {
                "message": "great success",
                "key": {
                    "id": "kid",
                    "description": "a new key",
                    "kind": "web",
                    "role": self.role,
                    "created_at": "",
                    "updated_at": "",
                    "expires_at": "",
                    "secret": "secret", # pragma: allowlist secret
                    "is_disabled": False,
                    "domain_name": "python.test.domain5",
                    "requestor": self.mailgun_email,
                    "user_name": self.user_name,
                },
            },
        )
        data = {
            "email": self.mailgun_email,
            "domain_name": "python.test.domain5",
            "kind": "web",
            "expiration": "3600",
            "role": self.role,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "description": "a new key",
        }
        headers = {"Content-Type": "multipart/form-data"}
        req = self.client.keys.create(data=data, headers=headers)
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json()["message"], "great success")
        self.assertIn("key", req.json())

    @patch("mailgun.client.requests.delete")
    @patch("mailgun.client.requests.get")
    def test_delete_key(self, m_get: MagicMock, m_delete: MagicMock) -> None:
        m_get.return_value = mock_response(
            200,
            {"items": [{"id": "key1", "requestor": self.mailgun_email}]},
        )
        m_delete.return_value = mock_response(200, {"message": "key deleted"})
        req1 = self.client.keys.get(filters={"domain_name": "python.test.domain5", "kind": "web"})
        for item in req1.json()["items"]:
            if self.mailgun_email == item["requestor"]:
                req2 = self.client.keys.delete(key_id=item["id"])
                self.assertEqual(req2.json()["message"], "key deleted")
                break

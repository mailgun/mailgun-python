"""A suite of tests for Mailgun Python SDK functionality."""

from __future__ import annotations

import json
import os
import string
import unittest
import random
from typing import Any

import pytest

from mailgun.client import Client


class MessagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.data: dict[str, str] = {
            "from": os.environ["MESSAGES_FROM"],
            "to": os.environ["MESSAGES_TO"],
            # TODO: Check 'Domain $DOMAIN is not allowed to send: Free accounts are for test purposes only. Please upgrade or add the address to authorized recipients in Account Settings.'
            # "cc": os.environ["MESSAGES_CC"],
            "subject": "Hello Vasyl Bodaj",
            "text": "Congratulations!, you just sent an email with Mailgun! You are truly awesome!",
            "o:tag": "Python test",
        }

    def test_post_right_message(self) -> None:
        req = self.client.messages.create(data=self.data, domain=self.domain)
        self.assertEqual(req.status_code, 200)

    def test_post_wrong_message(self) -> None:
        req = self.client.messages.create(data={"from": "sdsdsd"}, domain=self.domain)
        self.assertEqual(req.status_code, 400)


class DomainTests(unittest.TestCase):
    """All the tests of this part will work only on fresh setup, or if you change self.test_domain variable every time you're running this again.

    It's happening because domain name is not deleting permanently after API call, so every new create will cause an error,
    as that domain is still exists. To avoid the problems we use a random domain name generator.
    """

    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        random_domain_name = "".join(
            random.choice(string.ascii_lowercase + string.digits) for _ in range(10)
        )
        self.test_domain: str = f"mailgun.wrapper.{random_domain_name}"
        self.post_domain_data: dict[str, str] = {
            "name": self.test_domain,
        }
        self.put_domain_data: dict[str, str] = {
            "spam_action": "disabled",
        }
        self.post_domain_creds: dict[str, str] = {
            "login": f"alice_bob@{self.domain}",
            "password": "test_new_creds123",
        }

        self.put_domain_creds: dict[str, str] = {
            "password": "test_new_creds",
        }

        self.put_domain_connections_data: dict[str, str] = {
            "require_tls": "false",
            "skip_verification": "false",
        }

        self.put_domain_tracking_data: dict[str, str] = {
            "active": "yes",
            "skip_verification": "false",
        }
        # fmt: off
        self.put_domain_unsubscribe_data: dict[str, str] = {
            "active": "yes",
            "html_footer": "\n<br>\n<p><a href=\"%unsubscribe_url%\">UnSuBsCrIbE</a></p>\n",
            "text_footer": "\n\nTo unsubscribe here click: <%unsubscribe_url%>\n\n",
        }
        # fmt: on

        self.put_domain_dkim_authority_data: dict[str, str] = {
            "self": "false",
        }

        self.put_domain_webprefix_data: dict[str, str] = {
            "web_prefix": "python",
        }

        self.put_dkim_selector_data: dict[str, str] = {
            "dkim_selector": "s",
        }

    def tearDown(self) -> None:
        # We should be confident that the test domain has been deleted after DomainTests are complete,
        # otherwise, test_delete_domain and test_verify_domain will fail with a new run of tests
        self.client.domains.delete(domain=self.test_domain)

    def test_get_domain_list(self) -> None:
        req = self.client.domainlist.get()
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_post_domain(self) -> None:
        self.client.domains.delete(domain=self.test_domain)
        request = self.client.domains.create(data=self.post_domain_data)
        self.assertEqual(request.status_code, 200)
        self.assertIn("Domain DNS records have been created", request.json()["message"])

    def test_update_simple_domain(self) -> None:
        self.client.domains.delete(domain=self.test_domain)
        self.client.domains.create(data=self.post_domain_data)
        data = {"spam_action": "disabled"}
        request = self.client.domains.put(data=data, domain=self.post_domain_data['name'])
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.json()["message"], "Domain has been updated")

    @pytest.mark.skip("The test can fail because the domain name is a random string")
    def test_get_single_domain(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        req = self.client.domains.get(domain_name=self.post_domain_data["name"])

        self.assertEqual(req.status_code, 200)
        self.assertIn("domain", req.json())

    @pytest.mark.skip("The test can fail because the domain name is a random string")
    def test_verify_domain(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        req = self.client.domains.put(domain=self.post_domain_data["name"], verify=True)
        self.assertEqual(req.status_code, 200)
        self.assertIn("domain", req.json())

    def test_delete_domain(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains.delete(domain=self.test_domain)
        self.assertEqual(
            request.json()["message"],
            "Domain will be deleted in the background",
        )
        self.assertEqual(request.status_code, 200)

    def test_get_smtp_creds(self) -> None:
        request = self.client.domains_credentials.get(domain=self.domain)
        self.assertEqual(request.status_code, 200)
        self.assertIn("items", request.json())

    def test_post_domain_creds(self) -> None:
        request = self.client.domains_credentials.create(
            domain=self.domain,
            data=self.post_domain_creds,
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_put_domain_creds(self) -> None:
        self.client.domains_credentials.create(
            domain=self.domain,
            data=self.post_domain_creds,
        )
        request = self.client.domains_credentials.put(
            domain=self.domain,
            data=self.put_domain_creds,
            login="alice_bob",
        )

        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_delete_domain_creds(self) -> None:
        self.client.domains_credentials.create(
            domain=self.domain,
            data=self.post_domain_creds,
        )
        request = self.client.domains_credentials.delete(
            domain=self.domain,
            login="alice_bob",
        )

        self.assertEqual(request.status_code, 200)

    @pytest.mark.skip("If all credentials are deleted then test_update_simple_domain fails")
    def test_delete_all_domain_credentials(self) -> None:
        self.client.domains_credentials.create(
            domain=self.domain,
            data=self.post_domain_creds,
        )
        request = self.client.domains_credentials.delete(domain=self.domain)
        self.assertEqual(request.status_code, 200)
        self.assertIn(request.json()['message'],
                      "All domain credentials have been deleted")

    def test_put_domain_connections(self) -> None:
        request = self.client.domains_connection.put(
            domain=self.domain,
            data=self.put_domain_connections_data,
        )

        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_put_domain_tracking_open(self) -> None:
        request = self.client.domains_tracking_open.put(
            domain=self.domain,
            data=self.put_domain_tracking_data,
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_put_domain_tracking_click(self) -> None:
        request = self.client.domains_tracking_click.put(
            domain=self.domain,
            data=self.put_domain_tracking_data,
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_put_domain_unsubscribe(self) -> None:
        request = self.client.domains_tracking_unsubscribe.put(
            domain=self.domain,
            data=self.put_domain_unsubscribe_data,
        )
        self.assertEqual(request.status_code, 200)
        self.assertIn("message", request.json())

    def test_put_dkim_authority(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_dkimauthority.put(
            domain=self.test_domain,
            data=self.put_domain_dkim_authority_data,
        )
        self.assertIn("message", request.json())

    def test_put_webprefix(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_webprefix.put(
            domain=self.test_domain,
            data=self.put_domain_webprefix_data,
        )
        self.assertIn("message", request.json())

    def test_put_dkim_selector(self) -> None:
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_dkimselector.put(
            domain=self.domain,
            data=self.put_dkim_selector_data,
        )
        self.assertIn("message", request.json())

    def test_get_sending_queues(self) -> None:
        self.client.domains.delete(domain=self.test_domain)
        self.client.domains.create(data=self.post_domain_data)
        request = self.client.domains_sendingqueues.get(domain=self.post_domain_data['name'])
        self.assertEqual(request.status_code, 200)
        self.assertIn("scheduled", request.json())


@pytest.mark.skip(
    "Dedicated IPs should be enabled for the domain, see https://app.mailgun.com/settings/dedicated-ips"
)
class IpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.ip_data: dict[str, str] = {
            "ip": os.environ["DOMAINS_DEDICATED_IP"],
        }

    def test_get_ip_from_domain(self) -> None:
        req = self.client.ips.get(domain=self.domain, params={"dedicated": "true"})
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    def test_get_ip_by_address(self) -> None:
        self.client.domains_ips.create(domain=self.domain, data=self.ip_data)
        req = self.client.ips.get(domain=self.domain, ip=self.ip_data["ip"])
        self.assertIn("ip", req.json())
        self.assertEqual(req.status_code, 200)

    def test_create_ip(self) -> None:
        request = self.client.domains_ips.create(domain=self.domain, data=self.ip_data)
        self.assertEqual("success", request.json()["message"])
        self.assertEqual(request.status_code, 200)

    def test_delete_ip(self) -> None:
        request = self.client.domains_ips.delete(
            domain=self.domain,
            ip=self.ip_data["ip"],
        )
        self.assertEqual("success", request.json()["message"])
        self.assertEqual(request.status_code, 200)


@pytest.mark.skip(
    "This feature can be disabled for an account, see https://app.mailgun.com/settings/ip-pools"
)
class IpPoolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.data: dict[str, str] = {
            "name": "test_pool",
            "description": "Test",
            "add_ip": os.environ["DOMAINS_DEDICATED_IP"],
        }
        self.patch_data: dict[str, str] = {
            "name": "test_pool1",
            "description": "Test1",
        }
        self.ippool_id: Any = ""

    def test_get_ippools(self) -> None:
        self.client.ippools.create(domain=self.domain, data=self.data)
        req = self.client.ippools.get(domain=self.domain)
        self.assertIn("ip_pools", req.json())
        self.assertEqual(req.status_code, 200)

    def test_patch_ippool(self) -> None:
        req_post = self.client.ippools.create(domain=self.domain, data=self.data)
        self.ippool_id = req_post.json()["pool_id"]

        req = self.client.ippools.patch(
            domain=self.domain,
            data=self.patch_data,
            pool_id=self.ippool_id,
        )
        self.assertEqual("success", req.json()["message"])
        self.assertEqual(req.status_code, 200)

    def test_link_domain_ippool(self) -> None:
        pool_create = self.client.ippools.create(domain=self.domain, data=self.data)
        self.ippool_id = pool_create.json()["pool_id"]
        self.client.ippools.patch(
            domain=self.domain,
            data=self.patch_data,
            pool_id=self.ippool_id,
        )
        data = {
            "pool_id": self.ippool_id,
        }
        req = self.client.domains_ips.create(domain=self.domain, data=data)

        self.assertIn("message", req.json())

    def test_delete_ippool(self) -> None:
        req = self.client.ippools.create(domain=self.domain, data=self.data)
        self.ippool_id = req.json()["pool_id"]
        req_del = self.client.ippools.delete(domain=self.domain, pool_id=self.ippool_id)
        self.assertEqual("started", req_del.json()["message"])


class EventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.params: dict[str, str] = {
            "event": "rejected",
        }

    def test_events_get(self) -> None:
        req = self.client.events.get(domain=self.domain)
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    def test_event_params(self) -> None:
        req = self.client.events.get(domain=self.domain, filters=self.params)

        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)


class TagsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.data: dict[str, str] = {
            "description": "Tests running",
        }
        self.put_tags_data: dict[str, str] = {
            "description": "Python testtt",
        }
        self.stats_params: dict[str, str] = {
            "event": "accepted",
        }
        self.tag_name: str = "Python test"

    def test_get_tags(self) -> None:
        req = self.client.tags.get(domain=self.domain)
        self.assertIn("items", req.json())
        self.assertEqual(req.status_code, 200)

    def test_tag_get_by_name(self) -> None:
        req = self.client.tags.get(domain=self.domain, tag_name=self.tag_name)
        self.assertIn("tag", req.json())
        self.assertEqual(req.status_code, 200)

    def test_tag_put(self) -> None:
        req = self.client.tags.put(
            domain=self.domain,
            tag_name=self.tag_name,
            data=self.put_tags_data,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_tags_stats_get(self) -> None:
        req = self.client.tags_stats.get(
            domain=self.domain,
            filters=self.stats_params,
            tag_name=self.tag_name,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("tag", req.json())

    def test_tags_stats_aggregate_get(self) -> None:
        req = self.client.tags_stats_aggregates_devices.get(
            domain=self.domain,
            filters=self.stats_params,
            tag_name=self.tag_name,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("tag", req.json())

    @pytest.mark.skip("it deletes tags and test_tag_get_by_name will fail")
    def test_delete_tags(self) -> None:
        req = self.client.tags.delete(domain=self.domain, tag_name=self.tag_name)

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class BouncesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.bounces_data: dict[str, int | str] = {
            "address": "test30@gmail.com",
            "code": 550,
            "error": "Test error",
        }

        self.bounces_json_data: str = """[{
        "address": "test121@i.ua",
        "code": "550",
        "error": "Test error2312"
    },
        {
            "address": "test122@gmail.com",
            "code": "550",
            "error": "Test error"
        }]"""

    def test_bounces_get(self) -> None:
        req = self.client.bounces.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_bounces_create(self) -> None:
        req = self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_bounces_get_address(self) -> None:
        self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        req = self.client.bounces.get(
            domain=self.domain,
            bounce_address=self.bounces_data["address"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_bounces_create_json(self) -> None:
        json_data = json.loads(self.bounces_json_data)
        for address in json_data:
            req = self.client.bounces.create(
                data=address,
                domain=self.domain,
                headers={"Content-type": "application/json"},
            )
            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    def test_bounces_delete_single(self) -> None:
        self.client.bounces.create(data=self.bounces_data, domain=self.domain)
        req = self.client.bounces.delete(
            domain=self.domain,
            bounce_address=self.bounces_data["address"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_bounces_delete_all(self) -> None:
        req = self.client.bounces.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class UnsubscribesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.unsub_data: dict[str, str] = {
            "address": "test@gmail.com",
            "tag": "unsub_test_tag",
        }

        self.unsub_json_data: str = """[{
                "address": "test1@gmail.com",
                "tags": ["some tag"],
                "error": "Test error2312"
            },
            {
                "address": "test2@gmail.com",
                "code": ["*"],
                "error": "Test error"
            },
            {
                "address": "test3@gmail.com"
            }]"""

    def test_unsub_create(self) -> None:
        req = self.client.unsubscribes.create(data=self.unsub_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_unsub_get(self) -> None:
        req = self.client.unsubscribes.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_unsub_get_single(self) -> None:
        req = self.client.unsubscribes.get(
            domain=self.domain,
            unsubscribe_address=self.unsub_data["address"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_unsub_create_multiple(self) -> None:
        json_data = json.loads(self.unsub_json_data)
        for address in json_data:
            req = self.client.unsubscribes.create(
                data=address,
                domain=self.domain,
                headers={"Content-type": "application/json"},
            )

            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    def test_unsub_delete(self) -> None:
        req = self.client.bounces.delete(
            domain=self.domain,
            unsubscribe_address=self.unsub_data["address"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_unsub_delete_all(self) -> None:
        req = self.client.bounces.delete(domain=self.domain)

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class ComplaintsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.compl_data: dict[str, str] = {
            "address": "test@gmail.com",
            "tag": "compl_test_tag",
        }

        self.compl_json_data: str = """[{
                "address": "test1@gmail.com",
                "tags": ["some tag"],
                "error": "Test error2312"
            },
            {
                "address": "test3@gmail.com"}]"""

    def test_compl_create(self) -> None:
        req = self.client.complaints.create(data=self.compl_data, domain=self.domain)

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_get_single_complaint(self) -> None:
        req = self.client.complaints.get(data=self.compl_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_compl_get_all(self) -> None:
        req = self.client.complaints.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_compl_get_single(self) -> None:
        self.client.complaints.create(data=self.compl_data, domain=self.domain)
        req = self.client.complaints.get(
            domain=self.domain,
            complaint_address=self.compl_data["address"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_compl_create_multiple(self) -> None:
        json_data = json.loads(self.compl_json_data)
        for address in json_data:
            req = self.client.complaints.create(
                data=address,
                domain=self.domain,
                headers={"Content-type": "application/json"},
            )

            self.assertEqual(req.status_code, 200)
            self.assertIn("message", req.json())

    def test_compl_delete_single(self) -> None:
        self.client.complaints.create(
            data=self.compl_json_data,
            domain=self.domain,
            headers="application/json",
        )
        req = self.client.complaints.delete(
            domain=self.domain,
            unsubscribe_address=self.compl_data["address"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_compl_delete_all(self) -> None:
        req = self.client.complaints.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class WhiteListTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.whitel_data: dict[str, str] = {
            "address": "test@gmail.com",
            "tag": "whitel_test",
        }

        self.whitl_json_data: list[dict[str, str]] = [
            {
                "address": "test1@gmail.com",
                "domain": self.domain,
            },
            {
                "address": "test3@gmail.com",
                "domain": self.domain,
            },
        ]

    def test_whitel_create(self) -> None:
        req = self.client.whitelists.create(data=self.whitel_data, domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_whitel_get_simple(self) -> None:
        self.client.whitelists.create(data=self.whitel_data, domain=self.domain)

        req = self.client.whitelists.get(
            domain=self.domain,
            whitelist_address=self.whitel_data["address"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("value", req.json())

    def test_whitel_delete_simple(self) -> None:
        self.client.whitelists.create(data=self.whitel_data, domain=self.domain)
        req = self.client.whitelists.delete(
            domain=self.domain,
            whitelist_address=self.whitel_data["address"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class RoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.routes_data: dict[str, int | str | list[str]] = {
            "priority": 0,
            "description": "Sample route",
            "expression": f"match_recipient('.*@{self.domain}')",
            "action": ["forward('http://myhost.com/messages/')", "stop()"],
        }
        self.routes_params: dict[str, int] = {
            "skip": 1,
            "limit": 1,
        }
        self.routes_put_data: dict[str, int] = {
            "priority": 2,
        }

    # 'Routes quota (1) is exceeded for a free plan
    def test_routes_create(self) -> None:
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        self.client.routes.delete(
            domain=self.domain,
            route_id=req1.json()["items"][0]["id"],
        )
        req = self.client.routes.create(domain=self.domain, data=self.routes_data)

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())

    def test_routes_get_all(self) -> None:
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        #  IndexError: list index out of range
        if len(req1.json()["items"]) > 0:
            self.client.routes.delete(
                domain=self.domain,
                route_id=req1.json()["items"][0]["id"],
            )
            self.client.routes.create(domain=self.domain, data=self.routes_data)
            req = self.client.routes.get(domain=self.domain, filters=self.routes_params)
        else:
            self.client.routes.create(domain=self.domain, data=self.routes_data)
            req = self.client.routes.get(domain=self.domain, filters=self.routes_params)

        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_get_route_by_id(self) -> None:
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        if len(req1.json()["items"]) > 0:
            self.client.routes.delete(
                domain=self.domain,
                route_id=req1.json()["items"][0]["id"],
            )

            req_post = self.client.routes.create(
                domain=self.domain, data=self.routes_data
            )
            self.client.routes.create(domain=self.domain, data=self.routes_data)
            req = self.client.routes.get(
                domain=self.domain, route_id=req_post.json()["route"]["id"]
            )
        else:
            req_post = self.client.routes.create(
                domain=self.domain, data=self.routes_data
            )
            self.client.routes.create(domain=self.domain, data=self.routes_data)
            req = self.client.routes.get(
                domain=self.domain, route_id=req_post.json()["route"]["id"]
            )

        self.assertEqual(req.status_code, 200)
        self.assertIn("route", req.json())

    def test_routes_put(self) -> None:
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        if len(req1.json()["items"]) > 0:
            self.client.routes.delete(
                domain=self.domain,
                route_id=req1.json()["items"][0]["id"],
            )
            req_post = self.client.routes.create(
                domain=self.domain, data=self.routes_data
            )
            req = self.client.routes.put(
                domain=self.domain,
                data=self.routes_put_data,
                route_id=req_post.json()["route"]["id"],
            )
        else:
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

    def test_routes_delete(self) -> None:
        params = {"skip": 0, "limit": 1}
        req1 = self.client.routes.get(domain=self.domain, filters=params)
        if len(req1.json()["items"]) > 0:
            self.client.routes.delete(
                domain=self.domain,
                route_id=req1.json()["items"][0]["id"],
            )
            req_post = self.client.routes.create(
                domain=self.domain, data=self.routes_data
            )

            req = self.client.routes.delete(
                domain=self.domain, route_id=req_post.json()["route"]["id"]
            )
        else:
            req_post = self.client.routes.create(
                domain=self.domain, data=self.routes_data
            )

            req = self.client.routes.delete(
                domain=self.domain, route_id=req_post.json()["route"]["id"]
            )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class WebhooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.webhooks_data: dict[str, str | list[str]] = {
            "id": "clicked",
            "url": ["https://i.ua"],
        }

        self.webhooks_data_put: dict[str, str] = {
            "url": "https://twitter.com",
        }

    def test_webhooks_create(self) -> None:
        req = self.client.domains_webhooks.create(
            domain=self.domain,
            data=self.webhooks_data,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    def test_webhooks_get(self) -> None:
        req = self.client.domains_webhooks.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("webhooks", req.json())

    def test_webhook_put(self) -> None:
        self.client.domains_webhooks.create(domain=self.domain, data=self.webhooks_data)
        req = self.client.domains_webhooks_clicked.put(
            domain=self.domain,
            data=self.webhooks_data_put,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    def test_webhook_get_simple(self) -> None:
        self.client.domains_webhooks.create(domain=self.domain, data=self.webhooks_data)
        req = self.client.domains_webhooks_clicked.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("webhook", req.json())
        self.client.domains_webhooks_clicked.delete(domain=self.domain)

    def test_webhook_delete(self) -> None:
        self.client.domains_webhooks.create(domain=self.domain, data=self.webhooks_data)
        req = self.client.domains_webhooks_clicked.delete(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class MailingListsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.maillist_address: str = os.environ["MAILLIST_ADDRESS"]
        self.mailing_lists_data: dict[str, str] = {
            "address": f"python_sdk@{self.domain}",
            "description": "Mailgun developers list",
        }

        self.mailing_lists_data_update: dict[str, str] = {
            "description": "Mailgun developers list 121212",
        }

        self.mailing_lists_members_data: dict[str, bool | str] = {
            "subscribed": True,
            "address": "bar@example.com",
            "name": "Bob Bar",
            "description": "Developer",
            "vars": '{"age": 26}',
        }

        self.mailing_lists_members_put_data: dict[str, bool | str] = {
            "subscribed": True,
            "address": "bar@example.com",
            "name": "Bob Bar",
            "description": "Developer",
            "vars": '{"age": 28}',
        }

        self.mailing_lists_members_data_mult: dict[str, bool | str] = {
            "upsert": True,
            "members": '[{"address": "Alice <alice@example.com>", "vars": {"age": 26}},'
            '{"name": "Bob", "address": "bob2@example.com", "vars": {"age": 34}}]',
        }

    def test_maillist_pages_get(self) -> None:
        req = self.client.lists_pages.get(domain=self.domain)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_maillist_lists_get(self) -> None:
        req = self.client.lists.get(domain=self.domain, address=self.maillist_address)
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    def test_maillist_lists_create(self) -> None:
        self.client.lists.delete(
            domain=self.domain,
            address=f"python_sdk@{self.domain}",
        )
        req = self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    def test_maillists_lists_put(self) -> None:
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)
        req = self.client.lists.put(
            domain=self.domain,
            data=self.mailing_lists_data_update,
            address=f"python_sdk@{self.domain}",
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("list", req.json())

    def test_maillists_lists_delete(self) -> None:
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)
        req = self.client.lists.delete(
            domain=self.domain,
            address=f"python_sdk@{self.domain}",
        )
        self.assertEqual(req.status_code, 200)
        # Recreate the mailing list so the other member lists tests succeed
        self.client.lists.create(domain=self.domain, data=self.mailing_lists_data)

    @pytest.mark.skip("Email Validations are only available for paid accounts")
    def test_maillists_lists_validate_create(self) -> None:
        req = self.client.lists.create(
            domain=self.domain,
            address=self.maillist_address,
            validate=True,
        )

        self.assertEqual(req.status_code, 202)
        self.assertIn("message", req.json())

    @pytest.mark.skip("Email Validations are only available for paid accounts")
    def test_maillists_lists_validate_get(self) -> None:
        req = self.client.lists.get(
            domain=self.domain,
            address=self.maillist_address,
            validate=True,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("id", req.json())

    @pytest.mark.skip("Email Validations are only available for paid accounts")
    def test_maillists_lists_validate_delete(self) -> None:
        self.client.lists.create(
            domain=self.domain,
            address=self.maillist_address,
            validate=True,
        )
        req = self.client.lists.get(
            domain=self.domain,
            address=self.maillist_address,
            validate=True,
        )

        self.assertEqual(req.status_code, 200)

    def test_maillists_lists_members_pages_get(self) -> None:
        req = self.client.lists_members_pages.get(
            domain=self.domain,
            address=self.maillist_address,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_maillists_lists_members_create(self) -> None:
        self.client.lists_members.delete(
            domain=self.domain,
            address=self.maillist_address,
            member_address=self.mailing_lists_members_data["address"],
        )
        req = self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("member", req.json())

    def test_maillists_lists_members_get(self) -> None:
        req = self.client.lists_members.get(domain=self.domain, address=self.maillist_address)
        self.assertEqual(req.status_code, 200)
        self.assertIn("items", req.json())

    def test_maillists_lists_members_update(self) -> None:
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

    def test_maillists_lists_members_delete(self) -> None:
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

    def test_maillists_lists_members_create_mult(self) -> None:
        req = self.client.lists_members.create(
            domain=self.domain,
            address=self.maillist_address,
            data=self.mailing_lists_members_data_mult,
            multiple=True,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("message", req.json())


class TemplatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.post_template_data: dict[str, str] = {
            "name": "template.name20",
            "description": "template description",
            "template": "{{fname}} {{lname}}",
            "engine": "handlebars",
            "comment": "version comment",
        }

        self.put_template_data: dict[str, str] = {
            "description": "new template description",
        }

        self.post_template_version_data: dict[str, str] = {
            "tag": "v11",
            "template": "{{fname}} {{lname}}",
            "engine": "handlebars",
            "active": "no",
        }
        self.put_template_version_data: dict[str, str] = {
            "template": "{{fname}} {{lname}}",
            "comment": "Updated version comment",
            "active": "no",
        }

        self.put_template_version: str = "v11"

    def test_create_template(self) -> None:
        self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
        )

        req = self.client.templates.create(
            data=self.post_template_data,
            domain=self.domain,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_get_template(self) -> None:
        params = {"active": "yes"}
        self.client.templates.create(data=self.post_template_data, domain=self.domain)
        req = self.client.templates.get(
            domain=self.domain,
            filters=params,
            template_name=self.post_template_data["name"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_put_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)
        req = self.client.templates.put(
            domain=self.domain,
            data=self.put_template_data,
            template_name=self.post_template_data["name"],
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_delete_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)
        req = self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
        )

        self.assertEqual(req.status_code, 200)

    def test_post_version_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)

        self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
            tag=self.put_template_version,
        )

        req = self.client.templates.create(
            data=self.post_template_version_data,
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )
        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_get_version_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)

        self.client.templates.create(
            data=self.post_template_version_data,
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )

        req = self.client.templates.get(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_put_version_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)

        self.client.templates.create(
            data=self.post_template_version_data,
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )

        req = self.client.templates.put(
            domain=self.domain,
            data=self.put_template_version_data,
            template_name=self.post_template_data["name"],
            versions=True,
            tag=self.put_template_version,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("template", req.json())

    def test_delete_version_template(self) -> None:
        self.client.templates.create(data=self.post_template_data, domain=self.domain)

        self.post_template_version_data["tag"] = "v0"
        self.post_template_version_data["active"] = "no"
        self.client.templates.create(
            data=self.post_template_version_data,
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
        )

        req = self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
            tag="v0",
        )

        self.client.templates.delete(
            domain=self.domain,
            template_name=self.post_template_data["name"],
            versions=True,
            tag=self.put_template_version,
        )

        self.assertEqual(req.status_code, 200)


@pytest.mark.skip(
    "Email Validation is only available through Mailgun paid plans, see https://www.mailgun.com/pricing/"
)
class EmailValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]
        self.validation_address_1: str = os.environ["VALIDATION_ADDRESS_1"]
        self.validation_address_2: str = os.environ["VALIDATION_ADDRESS_2"]

        self.get_params_address_validate: dict[str, str] = {
            "address": self.validation_address_1,
            "provider_lookup": "false",
        }

        self.post_params_address_validate: dict[str, str] = {
            "provider_lookup": "false",
        }
        self.post_address_validate: dict[str, str] = {
            "address": self.validation_address_1,
        }

    def test_post_address_validate(self) -> None:
        req = self.client.addressvalidate.create(
            domain=self.domain,
            data=self.post_address_validate,
            filters=self.post_params_address_validate,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_get_address_validate(self) -> None:
        req = self.client.addressvalidate.get(
            domain=self.domain,
            filters=self.get_params_address_validate,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("address", req.json())

    def test_get_bulk_address_validate_status(self) -> None:
        params = {"limit": 1}
        req = self.client.addressvalidate_bulk.get(domain=self.domain, filters=params)
        self.assertEqual(req.status_code, 200)
        self.assertIn("jobs", req.json())


@pytest.mark.skip(
    "Inbox Placement is only available through Mailgun Optimize plans, see https://help.mailgun.com/hc/en-us/articles/360034702773-Inbox-Placement"
)
class InboxPlacementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]

        self.post_inbox_test: dict[str, str] = {
            "domain": "domain.com",
            "from": "user@sending_domain.com",
            "subject": "testSubject",
            "html": "<html>HTML version of the body</html>",
        }

    def test_post_inbox_tests(self) -> None:
        req = self.client.inbox_tests.create(
            domain=self.domain,
            data=self.post_inbox_test,
        )

        self.assertEqual(req.status_code, 201)
        self.assertIn("tid", req.json())

    def test_get_inbox_tests(self) -> None:
        self.client.inbox_tests.create(domain=self.domain, data=self.post_inbox_test)
        req = self.client.inbox_tests.get(domain=self.domain)

        self.assertEqual(req.status_code, 200)
        self.assertIn("tests", req.json())

    def test_get_simple_inbox_tests(self) -> None:
        test_id = self.client.inbox_tests.create(
            domain=self.domain,
            data=self.post_inbox_test,
        )
        req = self.client.inbox_tests.get(
            domain=self.domain,
            test_id=test_id.json()["tid"],
        )

        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.json()["tid"], test_id.json()["tid"])

    def test_delete_inbox_tests(self) -> None:
        test_id = self.client.inbox_tests.create(
            domain=self.domain,
            data=self.post_inbox_test,
        )

        req = self.client.inbox_tests.delete(
            domain=self.domain,
            test_id=test_id.json()["tid"],
        )

        self.assertEqual(req.status_code, 200)

    def test_get_counters_inbox_tests(self) -> None:
        test_id = self.client.inbox_tests.create(
            domain=self.domain,
            data=self.post_inbox_test,
        )

        req = self.client.inbox_tests.get(
            domain=self.domain,
            test_id=test_id.json()["tid"],
            counters=True,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("counters", req.json())

    def test_get_checks_inbox_tests(self) -> None:
        test_id = self.client.inbox_tests.create(
            domain=self.domain,
            data=self.post_inbox_test,
        )

        req = self.client.inbox_tests.get(
            domain=self.domain,
            test_id=test_id.json()["tid"],
            checks=True,
        )

        self.assertEqual(req.status_code, 200)
        self.assertIn("checks", req.json())


class MetricsTest(unittest.TestCase):
    # "https://api.mailgun.net/v1/analytics/metrics"

    def setUp(self) -> None:
        self.auth: tuple[str, str] = (
            "api",
            os.environ["APIKEY"],
        )
        self.client: Client = Client(auth=self.auth)
        self.domain: str = os.environ["DOMAIN"]

        self.invalid_account_metrics_data = {
            "start": "Sun, 08 Jun 2025 00:00:00 +0000",
            "end": "Tue, 08 Jul 2025 00:00:00 +0000",
            "resolution": "century",
            "duration": "1c",
            "dimensions": ["time"],
            "metrics": [
                "accepted_count",
                "delivered_count",
                "clicked_rate",
                "opened_rate",
            ],
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
        self.account_metrics_data = {
            "start": "Sun, 08 Jun 2025 00:00:00 +0000",
            "end": "Tue, 08 Jul 2025 00:00:00 +0000",
            "resolution": "day",
            "duration": "1m",
            "dimensions": ["time"],
            "metrics": [
                "accepted_count",
                "delivered_count",
                "clicked_rate",
                "opened_rate",
            ],
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

        self.invalid_account_usage_metrics_data = {
            "start": "Sun, 08 Jun 2025 00:00:00 +0000",
            "end": "Tue, 08 Jul 2025 00:00:00 +0000",
            "resolution": "century",
            "duration": "1c",
            "dimensions": ["time"],
            "metrics": [
                "accessibility_count",
                "accessibility_failed_count",
                "domain_blocklist_monitoring_count",
            ],
            "include_subaccounts": True,
            "include_aggregates": True,
        }

        self.account_usage_metrics_data = {
            "start": "Sun, 08 Jun 2025 00:00:00 +0000",
            "end": "Tue, 08 Jul 2025 00:00:00 +0000",
            "resolution": "day",
            "duration": "1m",
            "dimensions": ["time"],
            "metrics": [
                "accessibility_count",
                "accessibility_failed_count",
                "domain_blocklist_monitoring_count",
                "email_preview_count",
                "email_preview_failed_count",
                "email_validation_bulk_count",
                "email_validation_count",
                "email_validation_list_count",
                "email_validation_mailgun_count",
                "email_validation_mailjet_count",
                "email_validation_public_count",
                "email_validation_single_count",
                "email_validation_valid_count",
                "image_validation_count",
                "image_validation_failed_count",
                "ip_blocklist_monitoring_count",
                "link_validation_count",
                "link_validation_failed_count",
                "processed_count",
                "seed_test_count",
            ],
            "include_subaccounts": True,
            "include_aggregates": True,
        }

    def test_post_query_get_account_metrics(self) -> None:
        """Happy Path with valid data."""
        req = self.client.analytics_metrics.create(
            data=self.account_metrics_data,
        )
        expected_keys = [
            "start",
            "end",
            "resolution",
            "duration",
            "dimensions",
            "pagination",
            "items",
            "aggregates",
        ]
        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 200)
        [self.assertIn(key, expected_keys) for key in req.json().keys()]  # type: ignore[func-returns-value]
        self.assertIn("metrics", req.json()["items"][0])
        self.assertIn("dimensions", req.json()["items"][0])
        self.assertIn("delivered_count", req.json()["items"][0]["metrics"])

    def test_post_query_get_account_metrics_invalid_data(self) -> None:
        """Expected failure with invalid data."""
        req = self.client.analytics_metrics.create(
            data=self.invalid_account_metrics_data,
        )

        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 400)
        self.assertNotIn("items", req.json())
        self.assertIn("'resolution' attribute is invalid", req.json()["message"])

    def test_post_query_get_account_metrics_invalid_url(self) -> None:
        """Expected failure with an invalid URL https://api.mailgun.net/v1/analytics_metric (without 's' at the end)"""
        req = self.client.analytics_metric.create(
            data=self.account_metrics_data,
        )
        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 404)

    def test_post_query_get_account_metrics_invalid_url_without_underscore(
        self,
    ) -> None:
        """Expected failure with an invalid URL https://api.mailgun.net/v1/analyticsmetric (without '_' in the middle)"""
        with self.assertRaises(KeyError) as cm:
            self.client.analyticsmetric.create(
                data=self.account_metrics_data,
            )
        self.assertEqual(str(cm.exception), "'analyticsmetric'")

    def test_post_query_get_account_usage_metrics(self) -> None:
        req = self.client.analytics_usage_metrics.create(
            data=self.account_usage_metrics_data,
        )
        expected_keys = [
            "start",
            "end",
            "resolution",
            "duration",
            "dimensions",
            "pagination",
            "items",
            "aggregates",
        ]
        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 200)
        [self.assertIn(key, expected_keys) for key in req.json().keys()]  # type: ignore[func-returns-value]
        self.assertIn("metrics", req.json()["items"][0])
        self.assertIn("dimensions", req.json()["items"][0])
        self.assertIn("email_validation_count", req.json()["items"][0]["metrics"])

    def test_post_query_get_account_usage_metrics_invalid_data(self) -> None:
        """Expected failure with invalid data."""
        req = self.client.analytics_usage_metrics.create(
            data=self.invalid_account_usage_metrics_data,
        )
        from pprint import pprint

        pprint(req.json())
        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 400)
        self.assertNotIn("items", req.json())
        self.assertIn("'resolution' attribute is invalid", req.json()["message"])

    def test_post_query_get_account_usage_metrics_invalid_url(self) -> None:
        """Expected failure with an invalid URL https://api.mailgun.net/v1/analytics_usage_metric (without 's' at the end)"""
        req = self.client.analytics_usage_metric.create(
            data=self.invalid_account_usage_metrics_data,
        )
        self.assertIsInstance(req.json(), dict)
        self.assertEqual(req.status_code, 404)

    def test_post_query_get_account_usage_metrics_invalid_url_without_underscore(
        self,
    ) -> None:
        """Expected failure with an invalid URL https://api.mailgun.net/v1/analyticsusagemetrics (without '_' in the middle)"""
        with self.assertRaises(KeyError) as cm:
            self.client.analyticsusagemetrics.create(
                data=json.dumps(self.invalid_account_usage_metrics_data),
            )
        self.assertEqual(str(cm.exception), "'analyticsusagemetrics'")


if __name__ == "__main__":
    unittest.main()

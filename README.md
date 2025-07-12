# Mailgun Python SDK

Welcome to the official Python SDK for [Mailgun](http://www.mailgun.com/)!

Check out all the resources and Python code examples in the official [Mailgun Documentation](https://documentation.mailgun.com/docs/mailgun/).

## Table of contents

- [Mailgun Python SDK](#mailgun-python-sdk)
  - [Table of contents](#table-of-contents)
  - [Compatibility](#compatibility)
  - [Requirements](#requirements)
    - [Build backend dependencies](#build-backend-dependencies)
    - [Runtime dependencies](#runtime-dependencies)
    - [Test dependencies](#test-dependencies)
  - [Installation](#installation)
    - [pip install](#pip-install)
      - [git clone & pip install locally](#git-clone--pip-install-locally)
      - [conda & make](#conda--make)
    - [For development](#for-development)
      - [Using conda](#using-conda)
  - [Overview](#overview)
    - [Base URL](#base-url)
    - [Authentication](#authentication)
    - [API Response Codes](#api-response-codes)
  - [Request examples](#request-examples)
    - [Full list of supported endpoints](#full-list-of-supported-endpoints)
    - [Messages](#messages)
      - [Send an email](#send-an-email)
      - [Send an email with attachments](#send-an-email-with-attachments)
      - [Send a scheduled message](#send-a-scheduled-message)
    - [Domains](#domains)
      - [Get domains](#get-domains)
      - [Get domains details](#get-domains-details)
      - [Create a domain](#create-a-domain)
      - [Update a domain](#update-a-domain)
      - [Domain connections](#domain-connections)
      - [Domain keys](#domain-keys)
        - [Update DKIM authority](#update-dkim-authority)
      - [Domain Tracking](#domain-tracking)
        - [Get tracking settings](#get-tracking-settings)
    - [Webhooks](#webhooks)
      - [Get all webhooks](#get-all-webhooks)
      - [Create a webhook](#create-a-webhook)
      - [Delete a webhook](#delete-a-webhook)
    - [Events](#events)
      - [Retrieves a paginated list of events](#retrieves-a-paginated-list-of-events)
      - [Get events by recipient](#get-events-by-recipient)
    - [Metrics](#metrics)
      - [Get account metrics](#get-account-metrics)
      - [Get account usage metrics](#get-account-usage-metrics)
    - [Suppressions](#suppressions)
      - [Bounces](#bounces)
        - [Create bounces](#create-bounces)
      - [Unsubscribe](#unsubscribe)
        - [View all unsubscribes](#view-all-unsubscribes)
        - [Import list of unsubscribes](#import-list-of-unsubscribes)
      - [Complaints](#complaints)
        - [Add complaints](#add-complaints)
        - [Import list of complaints](#import-list-of-complaints)
      - [Whitelists](#whitelists)
        - [Delete all whitelists](#delete-all-whitelists)
    - [Routes](#routes)
      - [Create a route](#create-a-route)
      - [Get a route by id](#get-a-route-by-id)
    - [Mailing Lists](#mailing-lists)
      - [Create a mailing list](#create-a-mailing-list)
      - [Get mailing lists members](#get-mailing-lists-members)
      - [Delete mailing lists address](#delete-mailing-lists-address)
    - [Templates](#templates)
      - [Get templates](#get-templates)
      - [Update a template](#update-a-template)
      - [Create a new template version](#create-a-new-template-version)
      - [Get all template's versions](#get-all-templates-versions)
    - [IP Pools](#ip-pools)
      - [Edit DIPP](#edit-dipp)
      - [Link an IP pool](#link-an-ip-pool)
    - [IPs](#ips)
      - [List account IPs](#list-account-ips)
      - [Delete a domain's IP](#delete-a-domains-ip)
    - [Tags](#tags)
      - [Get tags](#get-tags)
      - [Get aggregate countries](#get-aggregate-countries)
    - [Email validation](#email-validation)
      - [Create a single validation](#create-a-single-validation)
    - [Inbox placement](#inbox-placement)
      - [Get all inbox](#get-all-inbox)
  - [License](#license)
  - [Contribute](#contribute)
  - [Contributors](#contributors)

## Compatibility

This library `mailgun` officially supports the following Python versions:

- python >=3.10,\<3.14

It's tested up to 3.13 (including).

## Requirements

### Build backend dependencies

To build the `mailgun` package from the sources you need `setuptools` (as a build backend), `wheel`, and `setuptools-scm`.

### Runtime dependencies

At runtime the package requires only `requests >=2.32.4`.

### Test dependencies

For running test you need `pytest >=7.0.0` at least.
Make sure to provide the environment variables from [Authentication](#authentication).

## Installation

### pip install

Use the below code to install the Mailgun SDK for Python:

```bash
pip install mailgun
```

#### git clone & pip install locally

Use the below code to install it locally by cloning this repository:

```bash
git clone https://github.com/mailgun/mailgun-python
cd mailgun-python
```

```bash
pip install .
```

#### conda & make

Use the below code to install it locally by `conda` and `make` on Unix platforms:

```bash
make install
```

### For development

#### Using conda

on Linux or macOS:

```bash
git clone https://github.com/mailgun/mailgun-python
cd mailgun-python
```

- A basic environment with a minimum number of dependencies:

```bash
make dev
conda activate mailgun
```

- A full dev environment:

```bash
make dev-full
conda activate mailgun-dev
```

## Overview

The Mailgun API is part of the Sinch family and enables you to send, track, and receive email effortlessly.

### Base URL

All API calls referenced in our documentation start with a base URL. Mailgun allows the ability to send and receive email in both US and EU regions. Be sure to use the appropriate base URL based on which region you have created for your domain.

It is also important to note that Mailgun uses URI versioning for our API endpoints, and some endpoints may have different versions than others. Please reference the version stated in the URL for each endpoint.

For domains created in our US region the base URL is:

```sh
https://api.mailgun.net/
```

For domains created in our EU region the base URL is:

```sh
https://api.eu.mailgun.net/
```

Your Mailgun account may contain multiple sending domains. To avoid passing the domain name as a query parameter, most API URLs must include the name of the domain you are interested in:

```sh
https://api.mailgun.net/v3/mydomain.com
```

### Authentication

The Mailgun Send API uses your API key for authentication. [Grab](https://app.mailgun.com/settings/api_security) and save your Mailgun API credentials.

To run tests and examples please use virtualenv or conda environment with next environment variables:

```bash
export APIKEY="API_KEY"
export DOMAIN="DOMAIN_NAME"
export MESSAGES_FROM="Name Surname <mailgun@domain_name>"
export MESSAGES_TO="Name Surname <username@gmail.com>"
export MESSAGES_CC="Name Surname <username2@gmail.com>"
export DOMAINS_DEDICATED_IP="127.0.0.1"
export MAILLIST_ADDRESS="everyone@mailgun.domain.com"
export VALIDATION_ADDRESS_1="test1@i.ua"
export VALIDATION_ADDRESS_2="test2@gmail.com"
```

Initialize your [Mailgun](http://www.mailgun.com/) client:

```python
from mailgun.client import Client
import os

auth = ("api", os.environ["APIKEY"])
client = Client(auth=auth)
```

### API Response Codes

All of Mailgun's HTTP response codes follow standard HTTP definitions. For some additional information and troubleshooting steps, please see below.

**400** - Will typically contain a JSON response with a "message" key which contains a human readable message / action to interpret.

**403** - Auth error or access denied. Please ensure your API key is correct and that you are part of a group that has access to the desired resource.

**404** - Resource not found. NOTE: this one can be temporal as our system is an eventually-consistent system but requires diligence. If a JSON response is missing for a 404 - that's usually a sign that there was a mistake in the API request, such as a non-existing endpoint.

**429** - Mailgun does have rate limits in place to protect our system. Please retry these requests as defined in the response. In the unlikely case you encounter them and need them raised, please reach out to our support team.

**500** - Internal Error on the Mailgun side. Retries are recommended with exponential or logarithmic retry intervals. If the issue persists, please reach out to our support team.

## Request examples

### Full list of supported endpoints

> [!IMPORTANT]\
> This is a full list of supported endpoints this SDK provides [mailgun/examples](mailgun/examples)

### Messages

#### Send an email

Pass the components of the messages such as To, From, Subject, HTML and text parts, attachments, etc. Mailgun will build a MIME representation of the message and send it. Note: In order to send you must provide one of the following parameters: 'text', 'html', 'amp-html' or 'template'

```python
import os
from mailgun.client import Client

key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def post_message() -> None:
    # Messages
    # POST /<domain>/messages
    data = {
        "from": os.getenv("MESSAGES_FROM", "test@test.com"),
        "to": os.getenv("MESSAGES_TO", "recipient@example.com"),
        "subject": "Hello from python!",
        "text": "Hello world!",
        "o:tag": "Python test",
    }

    req = client.messages.create(data=data, domain=domain)
    print(req.json())
```

#### Send an email with attachments

```python
import os
from pathlib import Path
from mailgun.client import Client

key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def post_message() -> None:
    # Messages
    # POST /<domain>/messages
    data = {
        "from": os.getenv("MESSAGES_FROM", "test@test.com"),
        "to": os.getenv("MESSAGES_TO", "recipient@example.com"),
        "subject": "Hello from python!",
        "text": "Hello world!",
        "o:tag": "Python test",
    }

    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    files = [
        (
            "attachment",
            ("test1.txt", Path("test1.txt").read_bytes()),
        )
    ]

    req = client.messages.create(data=data, files=files, domain=domain)
    print(req.json())
```

#### Send a scheduled message

```python
def post_scheduled() -> None:
    # Scheduled message
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": html,
        "o:deliverytime": "Thu Jan 28 2021 14:00:03 EST",
    }

    req = client.messages.create(data=data, domain=domain)
    print(req.json())
```

### Domains

#### Get domains

```python
import os
from mailgun.client import Client

key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
client: Client = Client(auth=("api", key))


def get_domains() -> None:
    """
    GET /domains
    :return:
    """
    data = client.domainlist.get()
    print(data.json())
```

#### Get domains with filters

```python
def get_domains_with_filters() -> None:
    """
    GET /domains
    :return:
    """
    params = {"skip": 0, "limit": 1}
    data = client.domainlist.get(filters=params)
    print(data.json())
```

#### Get domains details

```python
def get_simple_domain() -> None:
    """
    GET /domains/<domain>
    :return:
    """
    domain_name = "python.test.domain4"
    data = client.domains.get(domain_name=domain_name)
    print(data.json())
```

#### Create a domain

```python
def add_domain() -> None:
    """
    POST /domains
    :return:
    """
    # Post domain
    data = {
        "name": "python.test.domain5",
        # "smtp_password": "random123456"
    }

    request = client.domains.create(data=data)
    print(request.json())
    print(request.status_code)
```

#### Update a domain

```python
def update_simple_domain() -> None:
    """
    PUT /domains/<domain>
    :return:
    """
    domain_name = "python.test.domain5"
    data = {"name": domain_name, "spam_action": "disabled"}
    request = client.domains.put(data=data, domain=domain_name)
    print(request.json())
```

#### Domain connections

```python
def get_connections() -> None:
    """
    GET /domains/<domain>/connection
    :return:
    """
    request = client.domains_connection.get(domain=domain)
    print(request.json())
```

#### Domain keys

##### Update DKIM authority

```python
def put_dkim_authority() -> None:
    """
    PUT /domains/<domain>/dkim_authority
    :return:
    """
    data = {"self": "false"}
    request = client.domains_dkimauthority.put(domain=domain, data=data)
    print(request.json())
```

#### Domain Tracking

##### Get tracking settings

```python
def get_tracking() -> None:
    """
    GET /domains/<domain>/tracking
    :return:
    """
    request = client.domains_tracking.get(domain=domain)
    print(request.json())
```

### Webhooks

#### Get all webhooks

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_webhooks() -> None:
    """
    GET /domains/<domain>/webhooks
    :return:
    """
    req = client.domains_webhooks.get(domain=domain)
    print(req.json())
```

#### Create a webhook

```python
def create_webhook() -> None:
    """
    POST /domains/<domain>/webhooks
    :return:
    """
    data = {"id": "clicked", "url": ["https://facebook.com"]}
    #
    req = client.domains_webhooks.create(domain=domain, data=data)
    print(req.json())
```

#### Delete a webhook

```python
def put_webhook() -> None:
    """
    PUT /domains/<domain>/webhooks/<webhookname>
    :return:
    """
    data = {"id": "clicked", "url": ["https://facebook.com", "https://google.com"]}

    req = client.domains_webhooks_clicked.put(domain=domain, data=data)
    print(req.json())
```

### Events

#### Retrieves a paginated list of events

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_domain_events() -> None:
    """
    GET /<domain>/events
    :return:
    """
    req = client.events.get(domain=domain)
    print(req.json())
```

#### Get events by recipient

```python
def events_by_recipient() -> None:
    """
    GET /<domain>/events
    :return:
    """
    params = {
        "begin": "Tue, 24 Nov 2020 09:00:00 -0000",
        "ascending": "yes",
        "limit": 10,
        "pretty": "yes",
        "recipient": os.environ["VALIDATION_ADDRESS_1"],
    }
    req = client.events.get(domain=domain, filters=params)
    print(req.json())
```

### Metrics

Mailgun collects many different events and generates event metrics which are available in your Control Panel.
This data is also available via our analytics metrics [API endpoint](https://documentation.mailgun.com/docs/mailgun/api-reference/openapi-final/tag/Metrics/#tag/Metrics).

#### Get account metrics

Get filtered metrics for an account

```python
def post_analytics_metrics() -> None:
    """
    # Metrics
    # POST /analytics/metrics
    :return:
    """

    data = {
        "start": "Sun, 08 Jun 2025 00:00:00 +0000",
        "end": "Tue, 08 Jul 2025 00:00:00 +0000",
        "resolution": "day",
        "duration": "1m",
        "dimensions": ["time"],
        "metrics": ["accepted_count", "delivered_count", "clicked_rate", "opened_rate"],
        "filter": {
            "AND": [
                {
                    "attribute": "domain",
                    "comparator": "=",
                    "values": [{"label": domain, "value": domain}],
                }
            ]
        },
        "include_subaccounts": True,
        "include_aggregates": True,
    }

    req = client.analytics_metrics.create(data=data)
    print(req.json())
```

#### Get account usage metrics

```python
def post_analytics_usage_metrics() -> None:
    """
    # Usage Metrics
    # POST /analytics/usage/metrics
    :return:
    """
    data = {
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

    req = client.analytics_usage_metrics.create(data=data)
    print(req.json())
```

### Suppressions

#### Bounces

##### Create bounces

```python
import os

from mailgun.client import Client

key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))

def post_bounces() -> None:
"""
POST /<domain>/bounces
:return:
"""
data = {"address": "test120@gmail.com", "code": 550, "error": "Test error"}
req = client.bounces.create(data=data, domain=domain)
print(req.json())
```

#### Unsubscribe

##### View all unsubscribes

```python
def get_unsubs() -> None:
    """
    GET /<domain>/unsubscribes
    :return:
    """
    req = client.unsubscribes.get(domain=domain)
    print(req.json())
```

##### Import list of unsubscribes

> [!IMPORTANT]
> It is strongly recommended that you open files in binary mode.
> Because the Content-Length header may be provided for you,
> and if it does this value will be set to the number of bytes in the file.
> Errors may occur if you open the file in text mode.

```python
def import_list_unsubs() -> None:
    """
    POST /<domain>/unsubscribes/import, Content-Type: multipart/form-data
    :return:
    """
    files = {
        "unsubscribe2_csv": Path(
            "mailgun/doc_tests/files/mailgun_unsubscribes.csv"
        ).read_bytes()
    }
    req = client.unsubscribes_import.create(domain=domain, files=files)
    print(req.json())
```

#### Complaints

##### Add complaints

```python
def add_complaints() -> None:
    """
    POST /<domain>/complaints
    :return:
    """
    data = {"address": "bob@gmail.com", "tag": "compl_test_tag"}
    req = client.complaints.create(data=data, domain=domain)
    print(req.json())
```

##### Import list of complaints

> [!IMPORTANT]
> It is strongly recommended that you open files in binary mode.
> Because the Content-Length header may be provided for you,
> and if it does this value will be set to the number of bytes in the file.
> Errors may occur if you open the file in text mode.

```python
def import_complaint_list() -> None:
    """
    POST /<domain>/complaints/import, Content-Type: multipart/form-data
    :return:
    """
    files = {
        "complaints_csv": Path(
            "mailgun/doc_tests/files/mailgun_complaints.csv"
        ).read_bytes()
    }
    req = client.complaints_import.create(domain=domain, files=files)
    print(req.json())
```

#### Whitelists

##### Delete all whitelists

```python
def delete_all_whitelists() -> None:
    """
    DELETE /<domain>/whitelists
    :return:
    """
    req = client.whitelists.delete(domain=domain)
    print(req.json())
```

### Routes

#### Create a route

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def post_routes() -> None:
    """
    POST /routes
    :return:
    """
    data = {
        "priority": 0,
        "description": "Sample route",
        "expression": f"match_recipient('.*@{domain}')",
        "action": ["forward('http://myhost.com/messages/')", "stop()"],
    }
    req = client.routes.create(domain=domain, data=data)
    print(req.json())
```

#### Get a route by id

```python
def get_route_by_id() -> None:
    """
    GET /routes/<id>
    :return:
    """
    req = client.routes.get(domain=domain, route_id="6012d994e8d489e24a127e79")
    print(req.json())
```

### Mailing Lists

#### Create a mailing list

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def post_lists() -> None:
    """
    POST /lists
    :return:
    """
    data = {
        "address": f"python_sdk2@{domain}",
        "description": "Mailgun developers list",
    }

    req = client.lists.create(domain=domain, data=data)
    print(req.json())
```

#### Get mailing lists members

```python
def get_lists_members() -> None:
    """
    GET /lists/<address>/members/pages
    :return:
    """
    req = client.lists_members_pages.get(domain=domain, address=mailing_list_address)
    print(req.json())
```

#### Delete mailing lists address

```python
def delete_lists_address() -> None:
    """
    DELETE /lists/<address>
    :return:
    """
    req = client.lists.delete(domain=domain, address=f"python_sdk2@{domain}")
    print(req.json())
```

### Templates

#### Get templates

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_domain_templates() -> None:
    """
    GET /<domain>/templates
    :return:
    """
    params = {"limit": 1}
    req = client.templates.get(domain=domain, filters=params)
    print(req.json())
```

#### Update a template

```python
def update_template() -> None:
    """
    PUT /<domain>/templates/<name>
    :return:
    """
    data = {"description": "new template description"}

    req = client.templates.put(data=data, domain=domain, template_name="template.name1")
    print(req.json())
```

#### Create a new template version

```python
def create_new_template_version() -> None:
    """
    POST /<domain>/templates/<template>/versions
    :return:
    """
    data = {
        "tag": "v1",
        "template": "{{fname}} {{lname}}",
        "engine": "handlebars",
        "active": "yes",
    }

    req = client.templates.create(
        data=data, domain=domain, template_name="template.name1", versions=True
    )
    print(req.json())
```

#### Get all template's versions

```python
def get_all_versions() -> None:
    """
    GET /<domain>/templates/<template>/versions
    :return:
    """
    req = client.templates.get(
        domain=domain, template_name="template.name1", versions=True
    )
    print(req.json())
```

### IP Pools

#### Edit DIPP

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def update_ippool() -> None:
    """
    PATCH /v1/ip_pools/{pool_id}
    :return:
    """
    data = {
        "name": "test_pool3",
        "description": "Test3",
    }
    req = client.ippools.patch(
        domain=domain, data=data, pool_id="60140bc1fee3e84dec5abeeb"
    )
    print(req.json())
```

#### Link an IP pool

```python
def link_ippool() -> None:
    """
    POST /v3/domains/{domain_name}/ips
    :return:
    """
    data = {"pool_id": "60140d220859fda7bab8bb6c"}
    req = client.domains_ips.create(domain=domain, data=data)
    print(req.json())
```

### IPs

#### List account IPs

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_ips() -> None:
    """
    GET /ips
    :return:
    """
    req = client.ips.get(domain=domain, filters={"dedicated": "true"})
    print(req.json())
```

#### Delete a domain's IP

```python
def delete_domain_ip() -> None:
    """
    DELETE /domains/<domain>/ips/<ip>
    :return:
    """
    request = client.domains_ips.delete(domain=domain, ip="161.38.194.10")
    print(request.json())
```

### Tags

#### Get tags

```python
def get_tags() -> None:
    """
    GET /<domain>/tags
    :return:
    """
    req = client.tags.get(domain=domain)
    print(req.json())
```

#### Get aggregate countries

```python
def get_aggregate_countries() -> None:
    """
    GET /<domain>/tags/<tag>/stats/aggregates/countries
    :return:
    """
    req = client.tags_stats_aggregates_countries.get(
        domain=domain, tag_name="September newsletter"
    )
    print(req.json())
```

### Email validation

#### Create a single validation

```python
def post_single_validate() -> None:
    """
    POST /v4/address/validate
    :return:
    """
    data = {"address": "test2@gmail.com"}
    params = {"provider_lookup": "false"}
    req = client.addressvalidate.create(domain=domain, data=data, filters=params)
    print(req.json())
```

### Inbox placement

#### Get all inbox

```python
def get_all_inbox() -> None:
    """
    GET /v3/inbox/tests
    :return:
    """
    req = client.inbox_tests.get(domain=domain)
    print(req.json())
```

## License

[Apache-2.0](https://choosealicense.com/licenses/apache-2.0/)

## Contribute

Mailgun loves developers. You can be part of this project!

This Python SDK is a great introduction to the open source world, check out the code!

Feel free to ask anything, and contribute:

- Fork the project.
- Create a new branch.
- Implement your feature or bug fix.
- Add documentation to it.
- Commit, push, open a pull request and voila.

If you have suggestions on how to improve the guides, please submit an issue in our [Official API Documentation](https://documentation.mailgun.com).

## Contributors

- [@diskovod](https://github.com/diskovod)
- [@skupriienko](https://github.com/skupriienko)

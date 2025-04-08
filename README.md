# Mailgun Python SDK

## Overview

Welcome to the official Python SDK for [Mailgun]!

Check out all the resources and Python code examples in the official [Mailgun Documentation][doc].

## Table of contents

- [Compatibility](#compatibility)
- [Installation](#installation)
- [Authentication](#authentication)
- [Make your first call](#make-your-first-call)
- [Overview](#overview)
  - [Base URL](#base-url)
  - [Authentication](#authentication)
  - [API Response Codes](#api-response-codes)
- [Request examples](#request-examples)
  - [Messages](#messages)
    - [Send an email](#send-an-email)
  - [Domains](#domains)
    - [Get domains](#get-domains)
    - [Create a domain](#create-a-domain)
    - [Domain connections](#domain-connections)
    - [Domain keys](#domain-keys)
      - [Update DKIM authority](#update-dkim-authority)
    - [Domain Tracking](#domain-tracking)
      - [Get tracking settings](#get-tracking-settings)
  - [Webhooks](#webhooks)
    - [Get all webhooks](#get-all-webhooks)
    - [Create a webhook](#create-a-webhook)
  - [Events](#events)
    - [Retrieves a paginated list of events](#retrieves-a-paginated-list-of-events)
  - [Reporting](#reporting)
    - [Stats](#stats)
      - [Totals for entire account](#totals-for-entire-account)
  - [Suppressions](#suppressions)
    - [Unsubscribe](#unsubscribe)
      - [View all unsubscribes](#view-all-unsubscribes)
      - [Import list of unsubscribes](#import-list-of-unsubscribes)
    - [Complaints](#complaints)
      - [Import list of complaints](#import-list-of-complaints)
  - [Routes](#routes)
    - [Create a routes](#create-a-route)
  - [Mailing Lists](#mailing-lists)
    - [Create a mailing list](#create-a-mailing-list)
  - [Templates](#templates)
    - [Get templates](#get-templates)
  - [IP Pools](#ip-pools)
    - [Edit DIPP](#edit-dipp)
  - [IPs](#ips)
    - [List account IPs](#list-account-ips)
- [Contribute](#contribute)
- [License](#license)
- [Authors](#authors)

## Compatibility

This library officially supports the following Python versions:

- v3.9+

## Installation

Use the below code to install the Mailgun SDK for Python:

```bash
pip install mailgun
```

## Overview

The Mailgun API is part of the Sinch family and enables you to send, track, and receive email effortlessly.

### Base URL

All API calls referenced in our documentation start with a base URL. Mailgun allows the ability to send and receive email in both US and EU regions. Be sure to use the appropriate base URL based on which region you have created for your domain.

It is also important to note that Mailgun uses URI versioning for our API endpoints, and some endpoints may have different versions than others. Please reference the version stated in the URL for each endpoint.

For domains created in our US region the base URL is:

```
https://api.mailgun.net/
```

For domains created in our EU region the base URL is:

```
https://api.eu.mailgun.net/
```

Your Mailgun account may contain multiple sending domains. To avoid passing the domain name as a query parameter, most API URLs must include the name of the domain you are interested in:

```
https://api.mailgun.net/v3/mydomain.com
```

### Authentication

The Mailgun Send API uses your API key for authentication. [Grab][api_credential] and save your Mailgun API credentials.

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

Initialize your [Mailgun] client:

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

Examples for available endpoints you will find under:

```
mailgun/examples
```

### Messages

#### Send an email

Pass the components of the messages such as To, From, Subject, HTML and text parts, attachments, etc. Mailgun will build a MIME representation of the message and send it. Note: In order to send you must provide one of the following parameters: 'text', 'html', 'amp-html' or 'template'

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
    data = client.domainlist.get(domain=domain)
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

### Reporting

#### Stats

##### Totals for entire account

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_stats_total() -> None:
    params = {"event": ["accepted", "delivered", "failed"], "duration": "1m"}

    req = client.stats_total.get(filters=params, domain=domain)
    print(req.json())
```

### Suppressions

#### Unsubscribe

##### View all unsubscribes

```python
import os

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_unsubs() -> None:
    """
    GET /<domain>/unsubscribes
    :return:
    """
    req = client.unsubscribes.get(domain=domain)
    print(req.json())
```

##### Import list of unsubscribes

> [!CAUTION]
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

##### Import list of complaints

> [!CAUTION]
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

## License

[Apache-2.0](https://choosealicense.com/licenses/apache-2.0/)

## Contributors

- [@diskovod](https://github.com/diskovod)
- [@skupriienko](https://github.com/skupriienko)

[api_credential]: https://app.mailgun.com/settings/api_security
[doc]: https://documentation.mailgun.com/docs/mailgun/
[mailgun]: http://www.mailgun.com/

````markdown
# Mailgun Python SDK

Welcome to the official Python SDK for [Mailgun](http://www.mailgun.com/)!

Check out all the resources and Python code examples in the official
[Mailgun Documentation](https://documentation.mailgun.com).

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
  - [Quick Start](#quick-start)
    - [Synchronous Client](#client)
    - [AsyncClient](#asyncclient)
  - [Usage](#usage)
    - [Logging & Debugging](#logging--debugging)
    - [Logging & Secure Redaction](#logging--secure-redaction)
    - [Timeout Configuration](#timeout-configuration)
    - [API Response Codes](#api-response-codes)
    - [IDE Autocompletion & DX](#ide-autocompletion--dx)
    - [Zero-Leak Sandbox Mode](#zero-leak-sandbox-mode)
    - [API Response Codes](#api-response-codes)
    - [Context Managers (Safe Resource Teardown)](#context-managers-safe-resource-teardown)
    - [Fluent Message Builder](#fluent-message-builder)
    - [Streaming Pagination](#streaming-pagination)
    - [Strict Payload Schemas](#strict-payload-schemas)
  - [API Reference](#request-examples)
    - [Full list of supported endpoints](#full-list-of-supported-endpoints)
    - [Messages](#messages)
      - [Send an email](#send-an-email)
      - [Send an email with advanced parameters (Tags, Testmode, STO)](#send-an-email-with-advanced-parameters-tags-testmode-sto)
      - [Send an email with attachments](#send-an-email-with-attachments)
      - [Send a scheduled message](#send-a-scheduled-message)
    - [Domains](#domains)
      - [Get domains](#get-domains)
      - [Get domains with filters](#get-domains-with-filters)
      - [Get domains details](#get-domains-details)
      - [Create a domain](#create-a-domain)
      - [Update a domain](#update-a-domain)
      - [Domain connections](#domain-connections)
    - [Domain keys](#domain-keys)
      - [List keys for all domains](#list-keys-for-all-domains)
      - [Create a domain key](#create-a-domain-key)
        - [Update DKIM authority](#update-dkim-authority)
      - [Domain Tracking](#domain-tracking)
        - [Get tracking settings](#get-tracking-settings)
    - [Webhooks](#webhooks)
      - [Create a webhook (v4 Multi-Event)](#create-a-webhook-v4-multi-event)
      - [Get all webhooks](#get-all-webhooks)
      - [Create Account-Level Webhooks (v1)](#create-account-level-webhooks-v1)
    - [Events](#events)
      - [Retrieves a paginated list of events](#retrieves-a-paginated-list-of-events)
      - [Get events by recipient](#get-events-by-recipient)
    - [Bounce Classification](#bounce-classification)
      - [List statistic v2](#list-statistic-v2)
    - [Tags New](#tags-new)
      - [Get account tags](#get-account-tags)
      - [Update account tag](#update-account-tag)
      - [Post query to list account tags or search for single tag](#post-query-to-list-account-tags-or-search-for-single-tag)
      - [Delete account tag](#delete-account-tag)
      - [Get account tag limit information](#get-account-tag-limit-information)
    - [Metrics & Logs](#metrics--logs)
      - [List Logs](#list-logs)
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
    - [Keys](#keys)
      - [List Mailgun API keys](#list-mailgun-api-keys)
      - [Create Mailgun API key](#create-mailgun-api-key)
    - [Credentials](#credentials)
      - [List Mailgun SMTP credential metadata for a given domain](#list-mailgun-smtp-credential-metadata-for-a-given-domain)
      - [Create Mailgun SMTP credentials for a given domain](#create-mailgun-smtp-credentials-for-a-given-domain)
    - [Users](#users)
      - [Get users on an account](#get-users-on-an-account)
      - [Get a user's details](#get-a-users-details)
    - [Validations & Optimize APIs](#validations--optimize-apis)
      - [Email validation](#email-validation)
        - [Create a single validation](#create-a-single-validation)
        - [Validate an email address](#validate-an-email-address)
      - [Inbox placement](#inbox-placement)
        - [Get all inbox](#get-all-inbox)
        - [Fetch InboxReady placement tests](#fetch-inboxready-placement-tests)
  - [Deprecation Warnings](#deprecation-warnings)
  - [Type Hinting](#type-hinting)
  - [License](#license)
  - [Contribute](#contribute)
  - [Security](#security)
  - [Contributors](#contributors)

## Compatibility

This library `mailgun` officially supports the following Python versions:

- python >=3.10,\<3.15

It's tested up to 3.14 (including).
It guarantees cross-platform compatibility across Linux, macOS, and Windows.


## Requirements

### Build backend dependencies

To build the `mailgun` package from the sources you need `setuptools` (as a build backend) and `setuptools-scm`.

### Runtime dependencies

At runtime the package requires `requests >=2.33.0`. For async support, it uses `httpx >=0.24` and `typing-extensions >=4.7.1` (for pre-3.11 backward compatibility).

### Test dependencies

For running test you need `pytest >=9.0.3`, `pytest-asyncio`, and `responses` at least. Make sure to provide the environment variables from [Authentication](#authentication).

## Installation

### pip install

Use the below command to install the Mailgun SDK for Python:  

```bash
pip install mailgun
````

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

All API calls referenced in our documentation start with a base URL. The Mailgun API has regional endpoints.

If you are using a proxy or a regional endpoint (such as the EU infrastructure), you can configure a custom `api_url` during initialization.

Ensure you pass the correct Base URL to your client configuration:

US: `https://api.mailgun.net` (Default)

EU: `https://api.eu.mailgun.net`

**⚠️ Important:** The `api_url` parameter must strictly be the **base host only** (e.g., `https://api.eu.mailgun.net`). Do **not** append API version paths (like `/v3` or `/v4`) to this string. The SDK's data-driven routing engine automatically appends the correct, endpoint-specific API version under the hood.

### Authentication

Authenticate your Client using a tuple of ("api", "YOUR_API_KEY"). Find your API key in the [Mailgun Control Panel](https://app.mailgun.com/settings/api_security).

To run tests and examples please use virtualenv or conda environment with next environment variables:

```bash
export APIKEY="API_KEY"  # pragma: allowlist secret
export DOMAIN="DOMAIN_NAME"
export MESSAGES_FROM="Name Surname <mailgun@domain_name>"
export MESSAGES_TO="Name Surname <username@example.com>"
export MESSAGES_CC="Name Surname <username2@example.com>"
export DOMAINS_DEDICATED_IP="127.0.0.1"
export MAILLIST_ADDRESS="everyone@mailgun.domain.com"
export VALIDATION_ADDRESS_1="test1@example.com"
export VALIDATION_ADDRESS_2="test2@example"
export MAILGUN_EMAIL="username@example.com"
export USER_ID="123456789012345678901234"
export USER_NAME="Name Surname"
export ROLE="admin"
```

## Quick Start

Synchronous and Asynchronous Clients.

### Synchronous Client

#### Client Lifecycle & Resource Management

Initialize your [Mailgun](http://www.mailgun.com/) client.

> [!TIP]
> **New in v1.7.0:** The SDK now utilizes connection pooling (`requests.Session`) under the hood to dramatically improve performance by reusing TLS connections.

**The Simple Variant (Backward Compatible)**
For simple scripts, lambdas, or single-request apps, you can initialize and use the client directly. Python's garbage collector will eventually clean up the connection.

```python
import os
from mailgun.client import Client

client = Client(auth=("api", os.environ["APIKEY"]))
client.messages.create(data={"to": "user@example.com"})
```

> [!WARNING]
> If you are running long-lived applications (like Celery workers, web servers, or high-volume loops), repeatedly initializing the `Client` without closing it can lead to socket leaks (`Too many open files`).
> For production applications, \**always use the client as a Context Manager* (`with`) or explicitly call `client.close()`. This ensures deterministic release of TCP connection pools.

**The Recommended Variant (Context Manager)**

```python
import os
from mailgun.client import Client

# Sockets are safely managed and closed automatically
with Client(auth=("api", os.environ["APIKEY"])) as client:
    client.messages.create(data={"to": "user@example.com"})
```

### AsyncClient

SDK provides native async version of the client to use in asynchronous applications. The AsyncClient offers the same functionality as the sync client but with non-blocking I/O, making it ideal for concurrent operations and integration with asyncio-based applications.

```python
import asyncio
import os
from mailgun.client import AsyncClient


async def main():
    # BEST PRACTICE: Use the async context manager for safe connection pooling
    # and automatic socket teardown.
    async with AsyncClient(auth=("api", "your-api-key")) as client:
        response = await client.messages.create(
            domain="YOUR_DOMAIN_NAME",
            data={
                "from": "Excited User <mailgun@YOUR_DOMAIN_NAME>",
                "to": ["bar@example.com"],
                "subject": "Hello from Async!",
                "text": "Testing Mailgun asynchronously!",
            },
        )
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
```

## Usage

Send a message with a Synchronous Client safely inside a context manager.

```python
import os
from mailgun import Client

# Send an email using context manager
with Client(auth=("api", os.environ["APIKEY"])) as client:
    response = client.messages.create(
        data={
            "from": "Excited User <mailgun@sandbox.mailgun.org>",
            "to": ["recipient@example.com"],
            "subject": "Hello from Mailgun Python SDK",
            "text": "Testing some Mailgun awesomeness!",
        }
    )

    print(response.status_code)
    print(response.json())
```

The `AsyncClient` provides async equivalents for all methods available in the sync `Client`. The method signatures and parameters are identical - simply add `await` when calling methods:

```python
import os
from mailgun import Client, AsyncClient

# Sync version
with Client(auth=("api", os.environ["APIKEY"])) as client:
    result = client.domainlist.get()

# Async version
async with AsyncClient(auth=("api", os.environ["APIKEY"])) as client:
    result = await client.domainlist.get()
```

For detailed examples of all available methods, parameters, and use cases, refer to the [mailgun/examples](mailgun/examples) section. All examples can be adapted to async by using `AsyncClient` and adding `await` to method calls.

### Logging, Debugging & Secure Redaction

The Mailgun SDK uses standard Python logging. To aid in debugging, you can enable `DEBUG` or `INFO` logs.

**Built-in Security:** The SDK includes a native `RedactingFilter`.
You can stream these logs to your centralized monitoring systems (Splunk, Datadog, ELK) knowing that all private `api-keys`, `pubkeys`, and webhook signing secrets are automatically scrubbed and replaced with `[REDACTED]`.

To enable detailed logging in your application, configure the logger before initializing the client:

```python
import logging
from mailgun import Client

# Enable DEBUG level for the Mailgun SDK logger
logging.getLogger("mailgun.client").setLevel(logging.DEBUG)

# Configure the basic console output (if not already configured in your app)
logging.basicConfig(format="%(levelname)s - %(name)s - %(message)s")

# Now, any API errors or requests will be printed to your console
with Client(auth=("api", "key-super-secret-12345")) as client:
    # API keys will be redacted:
    # "Sending request to https://api.mailgun.net/v3/messages with auth ('api', 'key-[REDACTED]')"
    client.domains.get()
```

### Timeout Configuration

By default, the SDK relies on the underlying HTTP client's standard timeouts. To prevent uncontrolled resource consumption (CWE-400) in high-throughput production environments, you can enforce strict global timeouts.

Timeouts can be passed as a single `float` (seconds for both connect and read) or a tuple (connect_timeout, read_timeout):

```python
from mailgun import Client

# 3.5 seconds to connect, 15 seconds to wait for the server response
with Client(auth=("api", "your-key"), timeout=(3.5, 15.0)) as client:
    # Execute safely timed API calls here
    pass
```

### IDE Autocompletion & DX

The `Client` utilizes a dynamic routing engine but is heavily optimized for modern Developer Experience (DX).

- **Introspection**: Calling `dir(client)` or using autocomplete in IDEs like VS Code or PyCharm will automatically expose all available API endpoints (e.g., `client.messages`, `client.domains`, `client.bounces`).
- **Security Guardrails**: If you accidentally print the client instance or an exception traceback occurs in your CI/CD logs, your API key is strictly redacted from memory dumps: (`'api', '***REDACTED***'`).
- **Performance**: JSON payloads are automatically minified before transit to save bandwidth on large batch requests, and internal route resolution is heavily cached in memory.

### Zero-Leak Sandbox Mode

For local development and CI/CD pipelines, the Mailgun SDK offers a native **Zero-Leak Sandbox Mode**. By initializing the client with `dry_run=True`, the SDK will safely intercept all network traffic locally.

This allows you to fully validate your SDK initialization, dynamic routing, and payload building without dispatching real HTTP requests to Mailgun servers. This prevents accidental spam, list mutations, or billing charges during testing.

```python
from mailgun.client import Client

# 1. Initialize the client in strict Sandbox Mode
with Client(auth=("api", "your-api-key"), dry_run=True) as client:
    # 2. Execute a state-changing API call
    response = client.messages.create(
        domain="yourdomain.com",
        data={
            "from": "sender@example.com",
            "to": "test@example.com",
            "subject": "Testing Sandbox",
            "text": "This will not actually send!",
        },
    )

    # 3. The SDK intercepts the I/O layer and returns a mock 200 OK response
    print(response.status_code)
    # Outputs: 200

    print(response.json())
    # Outputs: {"message": "Dry run successful - request intercepted", "id": "<dry-run-mock-id>"}
```

Key Behaviors in `dry_run` Mode:

- Local payload checks (like strict minification and JSON serialization) still execute.
- Security sanitization and path segment rules still execute.
- Deprecation warnings will still be raised if you use an outdated endpoint.
- `sys.audit` events and standard `logging` messages are still emitted, clearly marked with `DRY RUN: Intercepting request...`.

### API Response Codes

All of Mailgun's HTTP response codes follow standard HTTP definitions. For some additional information and
troubleshooting steps, please see below.

**400** - Bad Request (e.g., missing parameter). Will typically contain a JSON response with a "message" key which contains a human readable message / action
to interpret.

**401/403** - Auth error or access denied. Please ensure your API key is correct and that you are part of a group that has
access to the desired resource.

**404** - Resource not found. NOTE: this one can be temporal as our system is an eventually-consistent system but
requires diligence. If a JSON response is missing for a 404 - that's usually a sign that there was a mistake in the API
request, such as a non-existing endpoint.

**429** - Rate limit exceeded. Mailgun does have rate limits in place to protect our system. The SDK automatically retries these using Exponential Backoff. In the unlikely case you encounter them and need them raised, please reach out to our support team.

**500/502/503** - Internal Error on the Mailgun side. The SDK automatically retries these using Exponential Backoff.
If the issue persists, please reach out to our support team.

### Context Managers (Safe Resource Teardown)

Always use the `Client` or `AsyncClient` inside a `with` statement. This ensures that underlying TCP connection pools are safely closed and sensitive API keys are immediately purged from memory once the block exits, preventing resource leaks.

**Synchronous:**

```python
from mailgun import Client

with Client(auth=("api", "your-api-key")) as client:
    response = client.domains.get()
    print(response.json())
# Connection pool is closed and credentials are wiped from memory here.
```

**Asynchronous:**

```python
import asyncio
from mailgun import AsyncClient


async def main():
    async with AsyncClient(auth=("api", "your-api-key")) as client:
        response = await client.domains.get()
        print(response.json())


asyncio.run(main())
```

### Fluent Message Builder

Constructing complex multipart emails with custom variables (v:), custom headers (h:), and tracking options (o:) can be error-prone. The MailgunMessageBuilder abstracts this away while providing automatic security guardrails against massive file attachments (OOM) and Path Traversal (CWE-22).

```python
from mailgun import Client
from mailgun.builders import MailgunMessageBuilder

with Client(auth=("api", "your-api-key")) as client:
    payload, files = (
        MailgunMessageBuilder("support@yourdomain.com")
        .add_recipient("customer@example.com")
        .set_subject("Your Invoice")
        .set_text("Please find your invoice attached.")
        .add_custom_variable("invoice_id", 1234)  # Translates to "v:invoice_id"
        .add_custom_header("Reply-To", "billing@...")  # Translates to "h:Reply-To"
        .attach_file("/tmp/invoice_1234.pdf", safe_base_dir="/tmp/")  # Path Traversal guardrail
        # Define short, human-readable aliases for complex local file paths
        .attach_inline("assets/logos/logo_v2_final.png", cid="company_logo")
        .attach_inline("assets/signatures/ceo_sign.png", cid="ceo_signature")
        .set_html(
            """
            <html>
                <body>
                    <img src="cid:company_logo" alt="Company Logo"/><br/>
                    <p>Hello! Thank you for choosing us.</p><br/>
                    <img src="cid:ceo_signature" alt="CEO Signature"/>
                </body>
            </html>
            """
        )
        .build()
    )

    client.messages.create(domain="yourdomain.com", data=payload, files=files)
```

### Streaming Pagination

For endpoints that return massive datasets (like Events, Bounces, or Suppressions), loading all pages into memory can crash your application.
The `.stream()` method handles cursor-based pagination invisibly under the hood, yielding one item at a time.

```python
from mailgun import Client

with Client(auth=("api", "key")) as client:
    # Safely iterate through millions of events with a flat memory footprint
    for event in client.events.stream(domain="yourdomain.com", filters={"event": "bounced"}):
        print(f"Bounced: {event['recipient']}")
```

### Strict Payload Schemas

If you prefer to build your own dictionaries instead of using the builder, you can opt-in to `TypedDict` schemas for full IDE autocomplete and `mypy` compile-time safety.

```python
from mailgun import Client
from mailgun.types import SendMessagePayload

my_data: SendMessagePayload = {
    "from": "admin@domain.com",
    "to": ["user@example.com"],
    "subject": "Strictly Typed Request",
}

with Client(auth=("api", "key")) as client:
    client.messages.create(domain="domain.com", data=my_data)
```

### Readiness / Liveness Probe

```python
import sys
import os
from mailgun import Client

api_key = os.environ.get("MAILGUN_API_KEY")

with Client(auth=("api", api_key)) as client:
    if client.ping():
        print("Status: Healthy")
        sys.exit(0)  # Exit code 0 indicates success
    else:
        print("Status: Unhealthy")
        sys.exit(1)  # Exit code 1 triggers container restart/unready state
```

## Request examples

### Full list of supported endpoints

> [!IMPORTANT]
> This is a full list of supported endpoints this SDK provides [mailgun/examples](mailgun/examples)

### Messages

#### Send an email

Pass the components of the messages such as To, From, Subject, HTML and text parts, attachments, etc. Mailgun will build
a MIME representation of the message and send it. Note: In order to send you must provide one of the following
parameters: 'text', 'html', 'amp-html' or 'template'

```python
import os
from mailgun import Client

data = {
    "from": "test@test.com",
    "to": "recipient@example.com",
    "subject": "Hello from python!",
    "text": "Hello world!",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.messages.create(data=data)
```

#### Send an email with advanced parameters (Tags, Testmode, STO)

Because the SDK maps kwargs directly to the payload, it inherently supports all advanced Mailgun features without needing SDK updates. You can easily add custom variables (`v:`), options (`o:`), and Send Time Optimization (STO) directly to your data dictionary.

```python
import os
from mailgun import Client

data = {
    "from": "Excited User <mailgun@my-domain.com>",
    "to": ["recipient1@example.com", "recipient2@example.com"],
    "subject": "Advanced Mailgun Features",
    "text": "Testing out tags, custom variables, and testmode!",
    "o:tag": ["newsletter", "python-sdk"],  # Multiple tags
    "o:testmode": "yes",  # Validates payload without actually sending
    "o:deliverytime-optimize-period": "24h",  # Send Time Optimization
    "v:my-custom-id": "USER-12345",  # Custom user-defined variable
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.messages.create(data=data)
```

#### Send an email with attachments

It is strongly recommended that you open files in binary mode (`read_bytes()`).

```python
import os
from pathlib import Path
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    files = [("attachment", ("report.pdf", Path("report.pdf").read_bytes()))]
    # Assuming `data` is predefined like in the previous example
    req = client.messages.create(data=data, files=files)
```

#### Send a scheduled message

```python
import os
from mailgun import Client


def post_scheduled() -> None:
    # Scheduled message
    domain: str = os.environ["DOMAIN"]
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": "<html><body>Hello!</body></html>",
        "o:deliverytime": "Thu Jan 28 2021 14:00:03 EST",
    }

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        req = client.messages.create(data=data, domain=domain)
        print(req.json())
```

#### Send a MIME message

When using the .mimemessage endpoint, Mailgun strictly requires the payload to be sent as multipart/form-data. In Python, you trigger this by passing the raw MIME string via the files parameter, assigning it to the "message" key.

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

mime_string = (
    "From: sender@example.com\n"
    "To: recipient@example.com\n"
    "Subject: MIME Test\n"
    "Content-Type: text/plain; charset=utf-8\n\n"
    "This is a raw MIME message."
).encode("utf-8")

# Force multipart/form-data by passing `files`
with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.mimemessage.create(
        domain=domain,
        data={"to": "recipient@example.com"},
        files={"message": ("message.mime", mime_string)},
    )
    print(req.json())
```

### Domains

#### Get domains

```python
import os
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    data = client.domainlist.get()
    print(data.json())
```

#### Get domains with filters

```python
import os
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    data = client.domainlist.get(filters={"skip": 0, "limit": 10})
    print(data.json())
```

#### Get domains details

```python
import os
from mailgun import Client

domain_name = "python.test.com"

with Client(auth=("api", os.environ["APIKEY"])) as client:
    data = client.domains.get(domain_name=domain_name)
    print(data.json())
```

#### Create a domain

```python
import os
from mailgun import Client

data = {"name": "new.domain.com"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.domains.create(data=data)
```

#### Update a domain

```python
import os
from mailgun import Client


def update_simple_domain() -> None:
    """
    PUT /domains/<domain>
    :return:
    """
    domain_name = "python.test.domain5"
    data = {"name": domain_name, "spam_action": "disabled"}

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.domains.put(data=data, domain=domain_name)
        print(request.json())
```

#### Domain connections

```python
import os
from mailgun import Client


def get_connections() -> None:
    """
    GET /domains/<domain>/connection
    :return:
    """
    domain: str = os.environ["DOMAIN"]

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.domains_connection.get(domain=domain)
        print(request.json())
```

### Domain keys

#### List keys for all domains

List domain keys, and optionally filter by signing domain or selector. The page & limit data is only required when paging through the data.

```python
import os
from mailgun import Client


def get_dkim_keys() -> None:
    """
    GET /v1/dkim/keys
    :return:
    """
    data = {
        "page": "string",
        "limit": "0",
        "signing_domain": "python.test.domain5",
        "selector": "smtp",
    }

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.dkim_keys.get(data=data)
        print(request.json())
```

#### Create a domain key

Create a domain key.
Note that once private keys are created or imported they are never exported.
Alternatively, you can import an existing PEM file containing an RSA private key in PKCS #1, ASn.1 DER format.
Note, the pem can be passed as a file attachment or as a form-string parameter.

```python
import os
import re
import subprocess
from pathlib import Path
from mailgun import Client


def post_dkim_keys() -> None:
    """
    POST /v1/dkim/keys
    :return:
    """
    secret_key_filename: str = os.environ["SECRET_KEY_FILENAME"]
    secret_key_path: Path = Path(secret_key_filename)
    ALLOWED_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,255}$")

    # Private key PEM file must be generated in PKCS1 format. You need 'openssl' on your machine
    # example:
    # openssl genrsa -traditional -out .server.key 2048
    if not ALLOWED_FILENAME_RE.match(secret_key_filename):
        raise ValueError(f"Invalid filename: {secret_key_filename!r}")
    subprocess.run(
        ["openssl", "genrsa", "-traditional", "-out", secret_key_filename, "--", "2048"], check=True
    )

    files = [
        (
            "pem",
            ("server.key", secret_key_path.read_bytes()),
        )
    ]

    data = {
        "signing_domain": "python.test.domain5",
        "selector": "smtp",
        "bits": "2048",
        "pem": files,
    }

    headers = {"Content-Type": "multipart/form-data"}

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.dkim_keys.create(data=data, headers=headers, files=files)
        print(request.json())
```

##### Update DKIM authority

```python
import os
from mailgun import Client


def put_dkim_authority() -> None:
    """
    PUT /domains/<domain>/dkim_authority
    :return:
    """
    domain: str = os.environ["DOMAIN"]
    data = {"self": "false"}

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.domains_dkimauthority.put(domain=domain, data=data)
        print(request.json())
```

#### Domain Tracking

##### Get tracking settings

```python
import os
from mailgun import Client


def get_tracking() -> None:
    """
    GET /domains/<domain>/tracking
    :return:
    """
    domain: str = os.environ["DOMAIN"]

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        request = client.domains_tracking.get(domain=domain)
        print(request.json())
```

### Webhooks

The SDK utilizes Payload-Based Routing. You do not need to worry about calling `/v1`, `/v3`, or `/v4` APIs.
Simply use `client.domains_webhooks` and the SDK will automatically analyze your payload (e.g., looking for `event_types`) and upgrade the request to the modern `v4` multi-event API if applicable.

#### Create a webhook (v4 Multi-Event)

```python
import os
from mailgun import Client

data = {
    "event_types": "clicked,opened,delivered",  # Triggers v4 routing
    "url": "https://my-server.com/webhook",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.domains_webhooks.create(data=data)
```

#### Get all webhooks

```python
import os
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.domains_webhooks.get()
```

#### Create Account-Level Webhooks (v1)

```python
import os
from mailgun import Client

data = {"id": "clicked", "url": ["https://my-server.com/webhook"]}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.account_webhooks.create(data=data)
```

### Events

#### Retrieves a paginated list of events

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.events.get(domain=domain)
    print(req.json())
```

#### Get events by recipient

```python
import os
from mailgun import Client

params = {
    "begin": "Tue, 24 Nov 2025 09:00:00 -0000",
    "limit": 10,
    "recipient": "user@example.com",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.events.get(filters=params)
```

### Bounce Classification

[API endpoint](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/bounce-classification).

#### List statistic v2

Items that have no bounces and no delays(classified_failures_count==0) are not returned.

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

payload = {
    "start": "Wed, 12 Nov 2025 23:00:00 UTC",
    "end": "Thu, 13 Nov 2025 23:00:00 UTC",
    "resolution": "day",
    "duration": "24h0m0s",
    "dimensions": ["entity-name", "domain.name"],
    "metrics": [
        "critical_bounce_count",
        "non_critical_bounce_count",
        "critical_delay_count",
        "non_critical_delay_count",
        "delivered_smtp_count",
        "classified_failures_count",
        "critical_bounce_rate",
        "non_critical_bounce_rate",
        "critical_delay_rate",
        "non_critical_delay_rate",
    ],
    "filter": {
        "AND": [
            {
                "attribute": "domain.name",
                "comparator": "=",
                "values": [{"value": domain}],
            }
        ]
    },
    "include_subaccounts": True,
    "pagination": {"sort": "entity-name:asc", "limit": 10},
}

headers = {"Content-Type": "application/json"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.bounceclassification_metrics.create(data=payload, headers=headers)
    print(req.json())
```

### Tags New

Mailgun allows you to tag your email with unique identifiers. Tags are visible via our analytics tags
[API endpoint](https://documentation.mailgun.com/docs/inboxready/api-reference/optimize/mailgun/tags-new).

#### Get account tags

```python
import os
from mailgun import Client

data = {"pagination": {"sort": "lastseen:desc", "limit": 10}}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_tags.create(data=data)
```

#### Update account tag

Updates the tag description for an account.

```python
import os
from mailgun import Client

data = {
    "tag": "name-of-tag-to-update",
    "description": "updated tag description",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_tags.update(data=data)
    print(req.json())
```

#### Post query to list account tags or search for single tag

Gets the list of all tags, or filtered by tag prefix, for an account.

```python
import os
from mailgun import Client

data = {
    "pagination": {"sort": "lastseen:desc", "limit": 10},
    "include_subaccounts": True,
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_tags.create(data=data)
    print(req.json())
```

#### Delete account tag

Deletes the tag for an account.

```python
import os
from mailgun import Client

data = {"tag": "name-of-tag-to-delete"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_tags.delete(data=data)
    print(req.json())
```

#### Get account tag limit information

Gets the tag limit and current number of unique tags for an account.

```python
import os
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_tags_limits.get()
    print(req.json())
```

### Metrics & Logs

#### List Logs

Mailgun keeps track of every inbound and outbound message event and stores this log data. This data can be queried and
filtered to provide insights into the health of your email infrastructure
[API endpoint](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/logs/post-v1-analytics-logs).

Gets customer event logs for an account.

```python
import os
from mailgun import Client


def post_analytics_logs() -> None:
    """
    # Metrics
    # POST /analytics/logs
    :return:
    """
    domain: str = os.environ["DOMAIN"]

    data = {
        "start": "Wed, 24 Sep 2025 00:00:00 +0000",
        "end": "Thu, 25 Sep 2025 00:00:00 +0000",
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
        "pagination": {
            "sort": "timestamp:asc",
            "limit": 50,
        },
    }

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        req = client.analytics_logs.create(data=data)
        print(req.json())
```

#### Get account metrics

Mailgun collects many different events and generates event metrics which are available in your Control Panel. This data
is also available via our analytics metrics
[API endpoint](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/metrics).

Get filtered metrics for an account

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

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

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.analytics_metrics.create(data=data)
    print(req.json())
```

#### Get account usage metrics

```python
import os
from mailgun import Client


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

    with Client(auth=("api", os.environ["APIKEY"])) as client:
        req = client.analytics_usage_metrics.create(data=data)
        print(req.json())
```

### Suppressions

#### Bounces

##### Create bounces

```python
import os
from mailgun import Client

data = {"address": "test120@gmail.com", "code": 550, "error": "Test error"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.bounces.create(data=data)
```

#### Unsubscribe

##### View all unsubscribes

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.unsubscribes.get(domain=domain)
    print(req.json())
```

##### Import list of unsubscribes

> [!IMPORTANT] It is strongly recommended that you open files in binary mode. Because the Content-Length header may be
> provided for you, and if it does this value will be set to the number of bytes in the file. Errors may occur if you
> open the file in text mode.

```python
import os
from pathlib import Path
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    files = {
        "unsubscribe2_csv": Path("mailgun/doc_tests/files/mailgun_unsubscribes.csv").read_bytes()
    }
    req = client.unsubscribes_import.create(domain=domain, files=files)
    print(req.json())
```

#### Complaints

##### Add complaints

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {"address": "bob@gmail.com", "tag": "compl_test_tag"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.complaints.create(data=data, domain=domain)
    print(req.json())
```

##### Import list of complaints

> [!IMPORTANT] It is strongly recommended that you open files in binary mode. Because the Content-Length header may be
> provided for you, and if it does this value will be set to the number of bytes in the file. Errors may occur if you
> open the file in text mode.

```python
import os
from pathlib import Path
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    files = {"complaints_csv": Path("mailgun/doc_tests/files/mailgun_complaints.csv").read_bytes()}
    req = client.complaints_import.create(domain=domain, files=files)
    print(req.json())
```

#### Whitelists

##### Delete all whitelists

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.whitelists.delete(domain=domain)
    print(req.json())
```

### Routes

#### Create a route

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {
    "priority": 0,
    "description": "Sample route",
    "expression": f"match_recipient('.*@{domain}')",
    "action": ["forward('http://myhost.com/messages/')", "stop()"],
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.routes.create(domain=domain, data=data)
    print(req.json())
```

#### Get a route by id

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.routes.get(domain=domain, route_id="xxxxxxxx")
    print(req.json())
```

### Mailing Lists

#### Create a mailing list

```python
import os
from mailgun import Client

data = {
    "address": "developers@my-domain.com",
    "description": "Mailgun developers list",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.lists.create(data=data)
```

#### Get mailing lists members

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.lists_members_pages.get(domain=domain, address="developers@my-domain.com")
    print(req.json())
```

#### Delete mailing lists address

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.lists.delete(domain=domain, address=f"python_sdk2@{domain}")
    print(req.json())
```

### Templates

#### Get templates

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
params = {"limit": 1}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.templates.get(domain=domain, filters=params)
    print(req.json())
```

#### Update a template

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {"description": "new template description"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.templates.put(data=data, domain=domain, template_name="template.name1")
    print(req.json())
```

#### Create a new template version

```python
import os
from mailgun import Client

data = {
    "tag": "v1",
    "template": "{{fname}} {{lname}}",
    "engine": "handlebars",
    "active": "yes",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.templates.create(data=data, template_name="welcome.email", versions=True)
```

#### Get all template's versions

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.templates.get(domain=domain, template_name="template.name1", versions=True)
    print(req.json())
```

### IP Pools

#### Edit DIPP

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

data = {
    "name": "test_pool3",
    "description": "Test3",
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.ippools.patch(domain=domain, data=data, pool_id="1234567890")
    print(req.json())
```

#### Link an IP pool

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {"pool_id": "60140d220859fda7bab8bb6c"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.domains_ips.create(domain=domain, data=data)
    print(req.json())
```

### IPs

#### List account IPs

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.ips.get(domain=domain, filters={"dedicated": "true"})
    print(req.json())
```

#### Delete a domain's IP

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    request = client.domains_ips.delete(domain=domain, ip="100.111.222.222")
    print(request.json())
```

### Keys

The Keys API lets you view and manage api keys.

#### List Mailgun API keys

```python
import os
from mailgun import Client

query = {"domain_name": "python.test.domain5", "kind": "web"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.keys.get(filters=query)
    print(req.json())
```

#### Create Mailgun API key

```python
import os
from mailgun.client import Client


def post_keys() -> None:
    """
    POST /v1/keys

    This code generate a Web API key tied to the account user associated with the data inputted for the USER_EMAIL field and USER_ID  values.
    This is returned by the API in the "secret":"API_KEY" key/value pair. This key will authenticate the call (Get one's own user details) made to the /v5/users/me endpoint,   # pragma: allowlist secret
    and will return the user's data associated with the USER_EMAIL and USER_ID values.

    Important Notes:
    USER_EMAIL - The user login email address of the user that is trying to make the call to the /v5/users/me endpoint.
    SECONDS - How many seconds you want the key to be active before it expires.
    ROLE - The role of the API Key. This dictates what permissions the key has (https://help.mailgun.com/hc/en-us/articles/26016288026907-API-Key-Roles)
    USER_ID - The internal User ID of the user that is trying to call the /v5/users/me endpoint. This is present in the URL in the address bar when viewing the User details in the GUI or in Admin. Both will show /users/USER_ID in the address.
    DESCRIPTION - Description of the key.

    :return:
    """
    key: str = os.environ["APIKEY"]
    mailgun_email = os.environ["MAILGUN_EMAIL"]
    role = os.environ["ROLE"]
    user_id = os.environ["USER_ID"]
    user_name = os.environ["USER_NAME"]

    data = {
        "email": mailgun_email,
        "domain_name": "python.test.domain5",
        "kind": "web",
        "expiration": "3600",
        "role": role,
        "user_id": user_id,
        "user_name": user_name,
        "description": "a new key",
    }

    headers = {"Content-Type": "multipart/form-data"}

    with Client(auth=("api", key)) as client:
        req = client.keys.create(data=data, headers=headers)
        print(req.json())
```

### Credentials

#### List Mailgun SMTP credential metadata for a given domain

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    request = client.domains_credentials.get(domain=domain)
    print(request.json())
```

#### Create Mailgun SMTP credentials for a given domain

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {
    "login": f"alice_bob@{domain}",
    "password": "test_new_creds123",  # pragma: allowlist secret
}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    request = client.domains_credentials.create(domain=domain, data=data)
    print(request.json())
```

### Users

#### Get users on an account

```python
import os
from mailgun import Client

query = {"role": "admin", "limit": "0", "skip": "0"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.users.get(filters=query)
    print(req.json())
```

#### Get a user's details

```python
import os
from mailgun import Client

mailgun_email = os.environ["MAILGUN_EMAIL"]
role = os.environ["ROLE"]

query = {"role": role, "limit": "0", "skip": "0"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req1 = client.users.get(filters=query)
    users = req1.json()["users"]

    for user in users:
        if mailgun_email == user["email"]:
            req2 = client.users.get(user_id=user["id"])
            print(req2.json())
```

### Validations & Optimize APIs

Thanks to the dynamic routing engine, the SDK natively supports Mailgun's supplementary APIs (like Email Validation, InboxReady, and Send Time Optimization) out of the box, automatically handling the versioning (v4, v5, etc.).

#### Email validation

##### Create a single validation

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]
data = {"address": "test2@gmail.com"}
params = {"provider_lookup": "false"}

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.addressvalidate.create(domain=domain, data=data, filters=params)
    print(req.json())
```

##### Validate an email address

```python
import os
from mailgun import Client

# Note: Requires a paid Mailgun plan.
with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.addressvalidate.get(address="suspicious@example.com")
```

#### Inbox placement

##### Get all inbox

```python
import os
from mailgun import Client

domain: str = os.environ["DOMAIN"]

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.inbox_tests.get(domain=domain)
    print(req.json())
```

##### Fetch InboxReady placement tests

```python
import os
from mailgun import Client

with Client(auth=("api", os.environ["APIKEY"])) as client:
    req = client.inboxready_domains.get()
    print(req.json())
```

## Deprecation Warnings

The SDK includes an active Interceptor engine that protects your application from API drift.

If you attempt to call a legacy or deprecated Mailgun endpoint (such as the old `v3` address validation or `v1` bounce classification), the SDK will **not** break your code.
It will successfully execute the request but will emit a non-breaking Python `DeprecationWarning` and print a logger warning with instructions on which modern API endpoint to migrate to.

## Type Hinting

This SDK is fully type-hinted and compatible with static type checkers like `mypy` and `pyright`.

Because of the dynamic URL dispatch engine (`__getattr__`), IDEs may flag endpoints like `client.messages.create` as `Any`.
If you enforce strict typing in your application, you may safely ignore these specific dynamically dispatched calls.

## License

[Apache-2.0](https://choosealicense.com/licenses/apache-2.0/)

## Contribute

See for details [CONTRIBUTING.md](CONTRIBUTING.md)

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and our security policies.

### Enterprise Security Audit Hooks (PEP 578)

For Enterprise and SecOps environments, the Mailgun SDK acts as a security sensor. It emits native Python audit events (`sys.audit`) for Zero-Trust monitoring, including:

- Outbound network requests (Egress tracking)
- CRLF Header Injection attempts
- Control Character Injection attempts (CWE-20)
- Server-Side Request Forgery (SSRF) bypass attempts (CWE-918)

You can globally **opt-in** to have the SDK automatically listen to these events and pipe them to your standard `logging` infrastructure for SIEM integration:

```python
import logging
import os
from mailgun.client import Client
from mailgun.config import Config

logging.basicConfig(level=logging.INFO)

# Activate the PEP 578 Audit Listener globally during app startup
Config.enable_security_audit()

# Initialize the client safely
with Client(auth=("api", os.environ.get("APIKEY", "your-api-key"))) as client:
    # The audit hook will now automatically intercept and log events like:
    # "SECURITY AUDIT: Outbound API call tracked - GET https://api.mailgun.net/v3/domains"
    response = client.domains.get()
```

## Contributors

- [@diskovod](https://github.com/diskovod)
- [@skupriienko](https://github.com/skupriienko)
- [@erz9engel](https://github.com/erz9engel)

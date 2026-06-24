"""
Examples for managing Mailgun Templates and Template Builders.

This file demonstrates the strict API separation between:
1. Domain Templates (V3 API): Scoped to a specific domain (`client.templates`)
2. Account Templates (V4 API): Scoped globally to the account (`client.account_templates`)
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from mailgun.builders import MailgunTemplateBuilder
from mailgun.client import Client

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def domain_template_exists(client: Client, domain: str, template_name: str) -> bool:
    """Check if a V3 Domain template exists."""
    try:
        client.templates.get(domain=domain, template_name=template_name)
        return True
    except Exception:
        return False


def account_template_exists(client: Client, template_name: str) -> bool:
    """Check if a V4 Account template exists."""
    try:
        client.account_templates.get(template_name=template_name)
        return True
    except Exception:
        return False


# ==============================================================================
# PART 1: DOMAIN TEMPLATES (V3 API) - SYNCHRONOUS
# These operations REQUIRE the `domain` parameter.
# ==============================================================================


def create_domain_template_sync(api_key: str, domain: str, template_name: str) -> None:
    """POST /v3/<domain>/templates"""
    data: dict[str, Any] = {
        "name": template_name,
        "description": "template description",
        "template": "{{fname}} {{lname}}",
        "engine": "handlebars",
        "comment": "version comment",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.templates.create(data=data, domain=domain)
        print("POST Domain Template (Sync):", response.status_code)


def get_domain_templates_sync(api_key: str, domain: str) -> None:
    """GET /<domain>/templates"""
    filters: dict[str, int] = {"limit": 1}
    with Client(auth=("api", api_key)) as client:
        response = client.templates.get(domain=domain, filters=filters)
        print("GET Domain Templates (Sync):", response.status_code)


def get_template_sync(api_key: str, domain: str, template_name: str) -> None:
    """GET /<domain>/templates/<name>"""
    filters: dict[str, str] = {"active": "yes"}
    with Client(auth=("api", api_key)) as client:
        response = client.templates.get(domain=domain, filters=filters, template_name=template_name)
        print("GET Template (Sync):", response.status_code)


def update_template_sync(api_key: str, domain: str, template_name: str) -> None:
    """PUT /<domain>/templates/<name>"""
    data: dict[str, str] = {"description": "new template description"}
    with Client(auth=("api", api_key)) as client:
        response = client.templates.put(data=data, domain=domain, template_name=template_name)
        print("PUT Update Template (Sync):", response.status_code)


def create_new_template_version_sync(
    api_key: str, domain: str, template_name: str, tag_name: str
) -> None:
    """POST /<domain>/templates/<template>/versions"""
    data: dict[str, str] = {
        "tag": tag_name,
        "template": "{{fname}} {{lname}} updated",
        "engine": "handlebars",
        "active": "yes",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.templates.create(
            data=data, domain=domain, template_name=template_name, versions=True
        )
        print(f"POST Template Version '{tag_name}' (Sync):", response.status_code)


def get_all_versions_sync(api_key: str, domain: str, template_name: str) -> None:
    """GET /<domain>/templates/<template>/versions"""
    with Client(auth=("api", api_key)) as client:
        response = client.templates.get(domain=domain, template_name=template_name, versions=True)
        print("GET All Template Versions (Sync):", response.status_code)


def get_template_version_sync(api_key: str, domain: str, template_name: str, tag_name: str) -> None:
    """GET /<domain>/templates/<name>/versions/<tag>"""
    with Client(auth=("api", api_key)) as client:
        response = client.templates.get(
            domain=domain, template_name=template_name, versions=True, tag=tag_name
        )
        print(f"GET Template Version '{tag_name}' (Sync):", response.status_code)


def update_domain_template_version_sync(
    api_key: str, domain: str, template_name: str, tag_name: str
) -> None:
    """PUT /<domain>/templates/<name>/versions/<tag>"""
    data: dict[str, str] = {"template": "<h1>Hello {{fname}} {{lname}}</h1>", "comment": "Updated"}
    with Client(auth=("api", api_key)) as client:
        response = client.templates.put(
            domain=domain,
            data=data,
            template_name=template_name,
            versions=True,
            tag=tag_name,
        )
        print("PUT Domain Template Version (Sync):", response.status_code)


def update_template_version_copy_sync(
    api_key: str, domain: str, template_name: str, source_tag: str, target_tag: str
) -> None:
    """PUT /v3/{domain_name}/templates/{template_name}/versions/{version_name}/copy/{new_version_name}"""
    filters: dict[str, str] = {"comment": "An updated version comment"}
    with Client(auth=("api", api_key)) as client:
        response = client.templates.put(
            domain=domain,
            filters=filters,
            template_name=template_name,
            versions=True,
            tag=source_tag,
            copy=True,
            new_tag=target_tag,
        )
        print(
            f"PUT Copy Template Version '{source_tag}' to '{target_tag}' (Sync):",
            response.status_code,
        )


def delete_template_version_sync(
    api_key: str, domain: str, template_name: str, tag_name: str
) -> None:
    """DELETE /<domain>/templates/<template>/versions/<version>"""
    with Client(auth=("api", api_key)) as client:
        response = client.templates.delete(
            domain=domain, template_name=template_name, versions=True, tag=tag_name
        )
        print(f"DELETE Template Version '{tag_name}' (Sync):", response.status_code)


def delete_domain_template_sync(api_key: str, domain: str, template_name: str) -> None:
    """DELETE /v3/<domain>/templates/<name>"""
    with Client(auth=("api", api_key)) as client:
        response = client.templates.delete(domain=domain, template_name=template_name)
        print(f"DELETE Domain Template '{template_name}' (Sync):", response.status_code)


def delete_all_templates_sync(api_key: str, domain: str) -> None:
    """DELETE /<domain>/templates"""
    with Client(auth=("api", api_key)) as client:
        response = client.templates.delete(domain=domain)
        print("DELETE All Templates (Sync):", response.status_code)


# ==============================================================================
# PART 2: ACCOUNT TEMPLATES (V4 API) - SYNCHRONOUS
# These operations MUST NOT use the `domain` parameter.
# ==============================================================================


def create_account_template_sync(api_key: str, template_name: str) -> None:
    """POST /v4/accounts/templates"""
    data: dict[str, Any] = (
        MailgunTemplateBuilder(name=template_name)
        .set_description("V4 Account-scoped global template")
        .set_template_content("<h1>Global Invoice for {{name}}</h1>")
        .set_tag("v1")
        .build()
    )
    with Client(auth=("api", api_key)) as client:
        response = client.account_templates.create(data=data)
        print(f"POST Account Template (Sync): {response.status_code}")


def copy_account_template_sync(api_key: str, template_name: str) -> None:
    """PUT /v4/accounts/templates/{template}/copy"""
    data: dict[str, Any] = (
        MailgunTemplateBuilder()
        .set_description("Copying template to subaccounts")
        .set_template_content(
            " "
        )  # REQUIRED: dummy content to prevent 'No fields to update' 400 error
        .set_copy_requests(
            [
                {"account_id": "acc-123", "name": f"{template_name}-child1"},
            ]
        )
        .build()
    )
    with Client(auth=("api", api_key)) as client:
        response = client.account_templates.put(data=data, template_name=template_name, copy=True)
        # Note: If 'acc-123' is not a real subaccount, this correctly returns 400 Bad Request
        print(f"PUT Copy Account Template (Sync): {response.status_code}")


def update_account_template_version_sync(api_key: str, template_name: str, tag_name: str) -> None:
    """PUT /v4/accounts/templates/{template}/versions/{tag}"""
    data: dict[str, Any] = (
        MailgunTemplateBuilder()
        .set_template_content("<h1>Updated Global Invoice</h1> <p>Thank you!</p>")
        .set_active(active=True)
        .build()
    )
    with Client(auth=("api", api_key)) as client:
        response = client.account_templates.put(
            data=data, template_name=template_name, versions=True, tag=tag_name
        )
        print(f"PUT Update Account Version (Sync): {response.status_code}")


def delete_account_template_sync(api_key: str, template_name: str) -> None:
    """DELETE /v4/accounts/templates/<name>"""
    with Client(auth=("api", api_key)) as client:
        response = client.account_templates.delete(template_name=template_name)
        print(f"DELETE Account Template '{template_name}' (Sync):", response.status_code)


# ==============================================================================
# EXECUTION ORCHESTRATION
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables.")
        sys.exit(1)

    # Use UUIDs to prevent '400 Duplicate Template' errors across multiple test runs
    uid = uuid.uuid4().hex[:6]
    V3_DOMAIN_TMPL = f"v3-domain-{uid}"
    V4_ACCOUNT_TMPL = f"v4-account-{uid}"

    VERSION_TAG_1 = "v1"
    VERSION_TAG_2 = "v2"

    try:
        # --- 1. Domain Template Workflow (V3) ---
        print(f"\n--- Starting V3 Domain Flow: {V3_DOMAIN_TMPL} ---")

        # Core Lifecycle
        create_domain_template_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL)
        get_domain_templates_sync(API_KEY, DOMAIN)
        get_template_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL)
        update_template_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL)

        # Version Lifecycle
        create_new_template_version_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL, VERSION_TAG_1)
        get_all_versions_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL)
        get_template_version_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL, VERSION_TAG_1)
        update_domain_template_version_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL, VERSION_TAG_1)

        # V3 Copy & Version Deletion
        update_template_version_copy_sync(
            API_KEY, DOMAIN, V3_DOMAIN_TMPL, VERSION_TAG_1, VERSION_TAG_2
        )
        delete_template_version_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL, VERSION_TAG_2)

        # --- 2. Account Template Workflow (V4) ---
        print(f"\n--- Starting V4 Account Flow: {V4_ACCOUNT_TMPL} ---")

        with Client(auth=("api", API_KEY)) as sync_client:
            create_account_template_sync(API_KEY, V4_ACCOUNT_TMPL)

            # Verify the global template actually exists before copying/updating
            if account_template_exists(sync_client, V4_ACCOUNT_TMPL):
                copy_account_template_sync(API_KEY, V4_ACCOUNT_TMPL)
                update_account_template_version_sync(API_KEY, V4_ACCOUNT_TMPL, "v1")
            else:
                print(f"WARNING: Account template {V4_ACCOUNT_TMPL} not found. Skipping ops.")

    finally:
        print("\n==================================================")
        print("Idempotent Teardown: Purging test artifacts")
        print("==================================================")

        # Clean up V3 Domain artifacts
        try:
            delete_domain_template_sync(API_KEY, DOMAIN, V3_DOMAIN_TMPL)
        except Exception as exc:
            print(f"WARNING: Failed to delete domain template {V3_DOMAIN_TMPL}: {exc}")

        # Clean up V4 Account artifacts
        try:
            delete_account_template_sync(API_KEY, V4_ACCOUNT_TMPL)
        except Exception as exc:
            print(f"WARNING: Failed to delete account template {V4_ACCOUNT_TMPL}: {exc}")

        # Note: delete_all_templates_sync(API_KEY, DOMAIN) is intentionally omitted
        # from the finally block to prevent accidentally wiping out production templates!

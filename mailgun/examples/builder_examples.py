"""Examples for Mailgun Message Builders and Clients."""

import asyncio
import os

from mailgun.builders import MailgunMessageBuilder
from mailgun.client import AsyncClient, Client


def send_standard_email_sync(api_key: str, domain: str) -> None:
    """
    Example 1: Sending a standard email with text, HTML, and an attachment.
    (Synchronous Execution)
    """
    print("\n--- Sending Standard Email (Sync) ---")
    payload, files = (
        MailgunMessageBuilder(f"support@{domain}")
        .add_recipient("user1@example.com")
        .set_subject("Your Monthly Invoice")
        .set_text("Please find your invoice attached.")
        .set_html("<html><body><p>Please find your invoice attached.</p></body></html>")
        .add_custom_header("Reply-To", f"billing@{domain}")
        # Note: file must exist locally to attach
        # .attach_file("/tmp/invoice.pdf", safe_base_dir="/tmp/")
        .build()
    )
    print(f"Payload: {payload}")

    # Use the synchronous context manager to prevent requests.Session socket leaks
    with Client(auth=("api", api_key)) as client:
        req = client.messages.create(domain=domain, data=payload, files=files)
        print(req.json())


async def send_template_email_async(api_key: str, domain: str) -> None:
    """
    Example 2: Sending an email using Mailgun Templates with variables and fallbacks.
    (Asynchronous Execution)
    """
    print("\n--- Sending Template Email (Async) ---")
    payload, files = (
        MailgunMessageBuilder(f"marketing@{domain}")
        .add_recipient("user2@example.com")
        .set_subject("Special Offer Inside!")
        .set_template("promo-template")
        .set_template_version("v2")
        .set_template_text(enable=True)  # Auto-generate text fallback for deliverability
        .set_template_variables({"discount": "20%", "code": "SAVE20"})
        .build()
    )
    print(f"Payload: {payload}")

    async with AsyncClient(auth=("api", api_key)) as client:
        req = await client.messages.create(domain=domain, data=payload, files=files)
        print(req.json())


def send_batch_email_sync(api_key: str, domain: str) -> None:
    """
    Example 3: Batch sending to up to 1,000 users with personalized variables.
    (Synchronous Execution)
    """
    print("\n--- Sending Batch Email (Sync) ---")
    payload, files = (
        MailgunMessageBuilder(f"newsletter@{domain}")
        .add_recipient("alice@example.com")
        .add_recipient("bob@example.com")
        .set_subject("Hey %recipient.name%, your weekly update!")
        .set_text("Hi %recipient.name%, your user ID is %recipient.id%.")
        .set_recipient_variables(
            {
                "alice@example.com": {"name": "Alice", "id": 101},
                "bob@example.com": {"name": "Bob", "id": 102},
            }
        )
        .build()
    )
    print(f"Payload: {payload}")

    with Client(auth=("api", api_key)) as client:
        req = client.messages.create(domain=domain, data=payload, files=files)
        print(req.json())


async def send_amp_and_inline_images_async(api_key: str, domain: str) -> None:
    """
    Example 4: Sending interactive AMP HTML with inline CID images.
    (Asynchronous Execution)
    """
    print("\n--- Sending AMP Email with Inline Image (Async) ---")

    dummy_image_path: str = "/tmp/logo.png"

    # Create a dummy image for this example to work
    try:
        with open(dummy_image_path, "wb") as f:
            f.write(b"dummy image data")

        payload, files = (
            MailgunMessageBuilder(f"hello@{domain}")
            .add_recipient("user3@example.com")
            .set_subject("Interactive Email")
            .set_html('<html><body><img src="cid:logo.png"></body></html>')
            .set_amp_html("<!doctype html><html \u26a14email><body>AMP Content</body></html>")
            .attach_inline(dummy_image_path, safe_base_dir="/tmp/")
            .build()
        )
        print(f"Payload: {payload}")
        print(f"Files: {[(f[0], f[1][0]) for f in files] if files else None}")

        async with AsyncClient(auth=("api", api_key)) as client:
            req = await client.messages.create(domain=domain, data=payload, files=files)
            print(req.json())

    finally:
        # Clean up the dummy image to avoid polluting the host's /tmp/ directory
        if os.path.exists(dummy_image_path):
            os.remove(dummy_image_path)


if __name__ == "__main__":
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        # 1. Run Synchronous Examples
        send_standard_email_sync(api_key=API_KEY, domain=DOMAIN)
        send_batch_email_sync(api_key=API_KEY, domain=DOMAIN)

        # 2. Run Asynchronous Examples
        asyncio.run(send_template_email_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(send_amp_and_inline_images_async(api_key=API_KEY, domain=DOMAIN))

"""Examples for Mailgun Message Builders and Clients."""

import asyncio
import logging
import os

from mailgun.builders import MailgunMessageBuilder
from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import DeliverabilityError


logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def send_standard_email_sync(api_key: str, domain: str) -> None:
    """
    Example 1: Sending a standard email with text, HTML, and an attachment.
    (Synchronous Execution)
    """
    print("\n--- Sending Standard Email (Sync) ---")

    payload, files = (
        MailgunMessageBuilder(f"support@{domain}")
        .add_recipient(MESSAGES_TO)
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
        .add_recipient(MESSAGES_TO)
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
        .add_recipient(MESSAGES_TO)
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
            .add_recipient(MESSAGES_TO)
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


def send_marketing_campaign(api_key: str, domain: str):
    html_content = """
    <html>
    <body>
        <h1>Welcome!</h1>
        <img src="https://mycdn.com/logo.png" />

        <script>alert('Track this');</script>
    </body>
    </html>
    """
    builder = MailgunMessageBuilder(f"support@{domain}").set_html(html_content)

    report = builder.check_deliverability()

    if not report["is_safe"]:
        raise DeliverabilityError(score=report["score"], issues=report["issues"])

    logger.info("Template is safe. Proceeding to send...")

    payload, files = (
        builder.add_recipient(MESSAGES_TO)
        .set_subject("Your Monthly Invoice")
        .set_text("Please find your invoice attached.")
        .build()
    )
    print(f"Payload: {payload}")

    with Client(auth=("api", api_key)) as client:
        req = client.messages.create(domain=domain, data=payload, files=files)
        print(req.json())


def send_large_report_sync(api_key: str, domain: str) -> None:
    """
    Example: Sending a massive 20MB monthly report safely without spiking RAM.
    """
    print("\n--- Sending Large Report Safely ---")

    test_file = "large_report.pdf"
    with open(test_file, "wb") as f:
        f.write(os.urandom(20 * 1024 * 1024))

    try:
        payload, files = (
            MailgunMessageBuilder(f"mailgun@{domain}")
            .add_recipient(MESSAGES_TO)
            .set_subject("Monthly Enterprise Report")
            .set_text("Here is the 20MB data export.")
            .attach_stream(test_file)
            .build()
        )

        # Increase read/write timeout to 300 sec,
        # but keep 10 sec for connection timeout.
        custom_timeout = (10.0, 300.0)

        with Client(auth=("api", api_key), timeout=custom_timeout) as client:
            req = client.messages.create(domain=domain, data=payload, files=files)
            print("Success:", req.json())

    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


async def send_large_report_async(api_key: str, domain: str) -> None:
    """
    Example: Asynchronously sending a massive 20MB monthly report safely
    without spiking RAM or blocking the event loop (CWE-400 Defense).
    """
    print("\n--- Sending Large Report Safely (Async) ---")

    test_file = "large_report_async.pdf"

    # Generate a dummy 20MB file synchronously for setup
    with open(test_file, "wb") as f:
        f.write(os.urandom(20 * 1024 * 1024))

    try:
        # 1. Build the payload and attach the streamer
        payload, files = (
            MailgunMessageBuilder(f"mailgun@{domain}")
            .add_recipient(MESSAGES_TO)
            .set_subject("Monthly Enterprise Report (Async)")
            .set_text("Here is the 20MB data export sent securely via asyncio.")
            .attach_stream(test_file)
            .build()
        )

        # Increase read/write timeout to 300 sec,
        # but keep 10 sec for connection timeout.
        custom_timeout = (10.0, 300.0)

        # 2. Use the AsyncClient context manager
        async with AsyncClient(auth=("api", api_key), timeout=custom_timeout) as client:
            # 3. Await the request. Under the hood, httpx will detect the
            # ChunkedStreamer and iterate over __aiter__ automatically.
            req = await client.messages.create(domain=domain, data=payload, files=files)
            print("Success:", req.json())

    finally:
        # Clean up the dummy file
        if os.path.exists(test_file):
            os.remove(test_file)


def test_idempotency_guard_in_action(domain: str) -> None:
    """
    Demonstration of the automatic generation of the idempotency key (IdempotencyGuard).
    Proves the determinism of SHA-256 hashing when building the payload.
    """
    print("\n--- 🛡️ Testing IdempotencyGuard (Client-Side Exactly-Once) ---")

    # Scenario 1: Build the original transactional email
    builder1 = (
        MailgunMessageBuilder(f"mailgun@{domain}")
        .add_recipient(MESSAGES_TO)
        .set_subject("Invoice Payment #1024")
        .set_text("Your invoice for $50.00 has been successfully paid.")
    )
    payload1, _ = builder1.build()
    key1 = payload1.get("h:X-Idempotency-Key")
    print(f"👉 Payload 1 (Original):   {key1}")

    # Scenario 2: Build an identical email (simulate a retry after network drop)
    builder2 = (
        MailgunMessageBuilder(f"mailgun@{domain}")
        .add_recipient(MESSAGES_TO)
        .set_subject("Invoice Payment #1024")
        .set_text("Your invoice for $50.00 has been successfully paid.")
    )
    payload2, _ = builder2.build()
    key2 = payload2.get("h:X-Idempotency-Key")
    print(f"👉 Payload 2 (Duplicate):  {key2}")

    # Scenario 3: Change at least one character (different invoice number)
    builder3 = (
        MailgunMessageBuilder(f"mailgun@{domain}")
        .add_recipient(MESSAGES_TO)
        .set_subject("Invoice Payment #1025")  # CHANGED!
        .set_text("Your invoice for $50.00 has been successfully paid.")
    )
    payload3, _ = builder3.build()
    key3 = payload3.get("h:X-Idempotency-Key")
    print(f"👉 Payload 3 (New email):  {key3}")

    # Scenario 4: Developer explicitly disables protection
    builder4 = (
        MailgunMessageBuilder(f"mailgun@{domain}")
        .set_idempotency_safe(False)  # DISABLED!
        .add_recipient("customer@example.com")
        .set_subject("Invoice Payment #1024")
    )
    payload4, _ = builder4.build()

    # --- CONCLUSIONS (ASSERTIONS) ---
    print("\n--- 📊 Validation Results ---")
    if key1 == key2:
        print(
            "✅ SUCCESS: Keys 1 and 2 are identical. Mailgun will reject the duplicate upon network retry."
        )
    else:
        print("❌ ERROR: Duplicate keys differ!")

    if key1 != key3:
        print("✅ SUCCESS: Key 3 is unique. The new email will pass safely.")

    if "h:X-Idempotency-Key" not in payload4:
        print("✅ SUCCESS: Protection manually disabled. Idempotency header is missing.")


if __name__ == "__main__":
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")
    MESSAGES_TO = os.environ.get("MESSAGES_TO") or f"success@{DOMAIN}"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        # 1. Run Synchronous Examples
        send_standard_email_sync(api_key=API_KEY, domain=DOMAIN)
        send_batch_email_sync(api_key=API_KEY, domain=DOMAIN)

        send_large_report_sync(API_KEY, DOMAIN)

        test_idempotency_guard_in_action(DOMAIN)

        try:
            send_marketing_campaign(api_key=API_KEY, domain=DOMAIN)
        except DeliverabilityError as e:
            # The user gracefully catches the error and sees a clean, actionable message
            # without a terrifying system traceback.
            logger.error(f"Campaign aborted by SpamGuard:\n{e}")

        # 2. Run Asynchronous Examples
        asyncio.run(send_template_email_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(send_amp_and_inline_images_async(api_key=API_KEY, domain=DOMAIN))
        asyncio.run(send_large_report_async(API_KEY, DOMAIN))

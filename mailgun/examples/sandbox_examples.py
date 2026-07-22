# mailgun/examples/sandbox_examples.py
import asyncio
import logging
from mailgun.client import Client, AsyncClient
from mailgun.builders import MailgunMessageBuilder
from mailgun.ext.sandbox import LocalSandbox

# Enable logging to see the interceptor in action
logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_html_sandbox_preview() -> None:
    """
    Scenario 1: Visual Sandbox Preview for HTML Emails.
    """
    print("\n--- 🧪 Scenario 1: HTML Sandbox Previewer ---")

    payload, _ = (
        MailgunMessageBuilder("test@my-company.com")
        .add_recipient("customer@gmail.com")
        .set_subject("🎉 Your report is ready (Layout Test)")
        .set_html("""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
                <h2 style="color: #3B82F6;">Hello, this is a local test!</h2>
                <p>This email never left your computer.</p>
                <div style="padding: 20px; background: #F3F4F6; border-radius: 8px;">
                    <strong>LocalSandbox</strong> is completely decoupled from the HTTP client.
                </div>
            </div>
        """)
        .build()
    )

    # 1. Preview the layout using the external sandbox explicitly
    sandbox = LocalSandbox(open_browser=True)
    sandbox.intercept_and_preview(payload)

    # 2. Safely verify the HTTP pipeline logic using standard dry_run
    with Client(auth=("api", "fake-key"), dry_run=True) as client:
        response = client.messages.create(domain="my-company.com", data=payload)
        print("\nSystem response (HTML Email):")
        print(response.json())


def run_standard_route_mock() -> None:
    """
    Scenario 2: Core Network Mocking (dry_run).
    If you query a non-message endpoint (like /domains) with dry_run=True,
    the SDK gracefully returns a mock JSON response.
    """
    print("\n--- 🧪 Scenario 2: Standard Route Dry Run ---")

    with Client(auth=("api", "fake-key"), dry_run=True) as client:
        response = client.domains.get()

        print("\nSystem response (Domains API):")
        print(response.json())


async def run_async_text_sandbox_preview() -> None:
    """
    Scenario 3: Async execution with decoupled sandbox.
    """
    print("\n--- 🧪 Scenario 3: Async Execution & Sandbox ---")

    payload, _ = (
        MailgunMessageBuilder("test@my-company.com")
        .add_recipient("customer@gmail.com")
        .set_subject("Plain Text Fallback Test")
        .set_text("Hello,\n\nThis is a plain text email.\n\nBest,\nThe Mailgun Python SDK Team")
        .build()
    )

    sandbox = LocalSandbox(open_browser=False)
    sandbox.intercept_and_preview(payload)

    async with AsyncClient(auth=("api", "fake-key"), dry_run=True) as client:
        response = await client.messages.create(domain="my-company.com", data=payload)

        print("\nSystem response (Plain Text Email):")
        print(response.json())


if __name__ == "__main__":
    run_html_sandbox_preview()
    run_standard_route_mock()
    asyncio.run(run_async_text_sandbox_preview())

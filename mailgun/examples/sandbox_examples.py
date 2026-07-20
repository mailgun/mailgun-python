# mailgun/examples/sandbox_example.py
import asyncio
import logging
from mailgun.client import Client, AsyncClient
from mailgun.builders import MailgunMessageBuilder

# Enable logging to see the interceptor in action
logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_html_sandbox_preview() -> None:
    """
    Scenario 1: Visual Sandbox Preview for HTML Emails (Sync).
    Instead of hitting the network, the SDK intercepts the payload
    and opens the rendered HTML in your default browser.
    """
    print("\n--- 🧪 Scenario 1: HTML Sandbox Previewer ---")

    # Initialize the client with dry_run=True.
    # No real API_KEY is needed because the network layer is severed.
    with Client(auth=("api", "fake-key"), dry_run=True) as client:
        payload, _ = (
            MailgunMessageBuilder("test@my-company.com")
            .add_recipient("customer@gmail.com")
            .set_subject("🎉 Your report is ready (Layout Test)")
            .set_html("""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
                    <h2 style="color: #3B82F6;">Hello, this is a local test!</h2>
                    <p>This email never left your computer.</p>
                    <div style="padding: 20px; background: #F3F4F6; border-radius: 8px;">
                        <strong>LocalSandbox</strong> allows you to test the layout instantly.
                        It is now fully unified with the <code>dry_run</code> flag!
                    </div>
                    <button style="margin-top:20px; padding:10px 20px; background:#10B981; color:white; border:none; border-radius:5px;">
                        Pay Invoice
                    </button>
                </div>
            """)
            .build()
        )

        response = client.messages.create(domain="my-company.com", data=payload)

        print("\nSystem response (HTML Email):")
        print(response.json())


def run_standard_route_mock() -> None:
    """
    Scenario 2: Standard Route Interception (Sync).
    If you query a non-message endpoint (like /domains) with dry_run=True,
    the SDK gracefully returns a mock JSON response without opening a browser.
    """
    print("\n--- 🧪 Scenario 2: Standard Route Dry Run ---")

    with Client(auth=("api", "fake-key"), dry_run=True) as client:
        # Querying the domains endpoint
        response = client.domains.get()

        print("\nSystem response (Domains API):")
        print(response.json())


async def run_async_text_sandbox_preview() -> None:
    """
    Scenario 3: Visual Sandbox for Plain Text Emails (Async).
    Demonstrates the AsyncClient and how the sandbox automatically
    wraps plain text into a readable HTML <pre> format.
    """
    print("\n--- 🧪 Scenario 3: Async Plain Text Sandbox ---")

    async with AsyncClient(auth=("api", "fake-key"), dry_run=True) as client:
        payload, _ = (
            MailgunMessageBuilder("test@my-company.com")
            .add_recipient("customer@gmail.com")
            .set_subject("Plain Text Fallback Test")
            .set_text(
                "Hello,\n\n"
                "This is a plain text email.\n"
                "Notice how the LocalSandbox automatically detects the missing HTML\n"
                "and wraps this text in <pre> tags so it displays correctly in your browser.\n\n"
                "Best,\nThe Mailgun Python SDK Team"
            )
            .build()
        )

        response = await client.messages.create(domain="my-company.com", data=payload)

        print("\nSystem response (Plain Text Email):")
        print(response.json())


if __name__ == "__main__":
    # Execute all scenarios
    run_html_sandbox_preview()
    run_standard_route_mock()

    # Run the async scenario
    asyncio.run(run_async_text_sandbox_preview())

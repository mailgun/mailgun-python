import logging
from mailgun.client import Client, AsyncClient

logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_standard_route_mock() -> None:
    """
    Scenario: Core Network Mocking (dry_run).
    If you query an endpoint with dry_run=True, the SDK safely
    returns a mock JSON response without making an HTTP request.
    """
    print("\n--- 🧪 Dry Run Execution ---")
    with Client(auth=("api", "fake-key"), dry_run=True) as client:
        response = client.domains.get()
        print("\nSystem response (Intercepted):")
        print(response.json())


if __name__ == "__main__":
    run_standard_route_mock()

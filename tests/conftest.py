import pytest
from urllib.parse import urlparse

BASE_URL_V1: str = "https://api.mailgun.net/v1"
BASE_URL_V2: str = "https://api.mailgun.net/v"
BASE_URL_V3: str = "https://api.mailgun.net/v3"
BASE_URL_V4: str = "https://api.mailgun.net/v4"
BASE_URL_V5: str = "https://api.mailgun.net/v5"
TEST_DOMAIN: str = "example.com"
TEST_EMAIL: str = "user@example.com"
TEST_123: str = "test-123"

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-skipped", action="store_true", default=False, help="run skipped tests")

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-skipped"):
        # If --run-skipped is passed, remove the 'skip' marker from all tests
        for item in items:
            for marker in list(item.iter_markers()):
                if marker.name in ("skip", "skipif"):
                    item.own_markers.remove(marker)

def parse_domain_name(result: str) -> str:
    path = urlparse(result).path
    parts = [p for p in path.split("/") if p]

    # If the path: ['v3', 'example.com', 'events']
    if len(parts) >= 2:
        return parts[1]
    return parts[-1]

from urllib.parse import urlparse

API_VERSION: str = "v3"
BASE_URL: str = f"https://api.mailgun.net/{API_VERSION}/"
TEST_DOMAIN: str = "example.com"


def parse_domain_name(result: str) -> str:
    path = urlparse(result).path
    parts = [p for p in path.split("/") if p]

    # If the path: ['v3', 'example.com', 'events']
    if len(parts) >= 2:
        return parts[1]
    return parts[-1]

from urllib.parse import urlparse


BASE_URL_V1: str = f"https://api.mailgun.net/v1"
BASE_URL_V3: str = f"https://api.mailgun.net/v3"
BASE_URL_V4: str = f"https://api.mailgun.net/v4"
TEST_DOMAIN: str = "example.com"


def parse_domain_name(result: str) -> str:
    path = urlparse(result).path
    parts = [p for p in path.split("/") if p]

    # If the path: ['v3', 'example.com', 'events']
    if len(parts) >= 2:
        return parts[1]
    return parts[-1]

import os
import re
from pathlib import Path
from urllib.parse import urlparse

BASE_URL_V1: str = "https://api.mailgun.net/v1"
BASE_URL_V3: str = "https://api.mailgun.net/v3"
BASE_URL_V4: str = "https://api.mailgun.net/v4"
TEST_DOMAIN: str = "example.com"
TEST_EMAIL: str = "user@example.com"
TEST_123: str = "test-123"

secret_key_filename: str = os.environ["SECRET_KEY_FILENAME"]
secret_key_path: Path = Path(secret_key_filename)
ALLOWED_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,255}$")


def parse_domain_name(result: str) -> str:
    path = urlparse(result).path
    parts = [p for p in path.split("/") if p]

    # If the path: ['v3', 'example.com', 'events']
    if len(parts) >= 2:
        return parts[1]
    return parts[-1]

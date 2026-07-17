"""Examples for sending and managing Mailgun Messages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import UploadError


# The maximum message size Mailgun supports is 25MB,
# see https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/send-http#send-via-http
MAX_FILE_SIZE: int = 25 * 1024 * 1024  # 25 MB


# ==============================================================================
# Message Management (Synchronous)
# ==============================================================================


def post_message_sync(
    api_key: str,
    domain: str,
    from_email: str,
    to_email: str,
    cc_email: str,
    html_body: str,
    file_path_1: str,
    file_path_2: str,
) -> None:
    """
    POST /<domain>/messages
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tag": "Python test",
    }

    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    file_bytes_1: bytes = Path(file_path_1).read_bytes()
    file_bytes_2: bytes = Path(file_path_2).read_bytes()

    for file_content in (file_bytes_1, file_bytes_2):
        if len(file_content) > MAX_FILE_SIZE:
            raise UploadError("File too large")

    files: list[tuple[str, tuple[str, bytes]]] = [
        ("attachment", (Path(file_path_1).name, file_bytes_1)),
        ("attachment", (Path(file_path_2).name, file_bytes_2)),
    ]

    with Client(auth=("api", api_key)) as client:
        response = client.messages.create(data=data, files=files, domain=domain)
        print("POST Message (Sync):", response.json())


def post_message_tags_sync(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Message Tags
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tag": ["September newsletter", "newsletters"],
    }
    with Client(auth=("api", api_key)) as client:
        response = client.messages.create(data=data, domain=domain)
        print("POST Message Tags (Sync):", response.json())


def post_mime_sync(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, mime_file_path: str
) -> None:
    """
    Mime messages
    POST /<domain>/messages.mime
    :return: None
    """
    mime_data: dict[str, str] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello HELLO",
    }
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    # Mailgun requires the MIME string to be uploaded as a file
    # . Passing 'files' forces multipart/form-data.
    files: dict[str, bytes] = {"message": Path(mime_file_path).read_bytes()}

    with Client(auth=("api", api_key)) as client:
        response = client.mimemessage.create(data=mime_data, files=files, domain=domain)
        print("POST MIME (Sync):", response.json())


def post_no_tracking_sync(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Message no tracking
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tracking": False,
    }
    with Client(auth=("api", api_key)) as client:
        response = client.messages.create(data=data, domain=domain)
        print("POST No Tracking (Sync):", response.json())


def post_scheduled_sync(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Scheduled message
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:deliverytime": "Thu Jan 28 2021 14:00:03 EST",
    }
    with Client(auth=("api", api_key)) as client:
        response = client.messages.create(data=data, domain=domain)
        print("POST Scheduled (Sync):", response.json())


def resend_message_sync(api_key: str, domain: str, from_email: str, to_email: str) -> None:
    """
    Resend message
    :return: None
    """
    data: dict[str, list[str]] = {"to": ["test1@example.com", "test2@example.com"]}
    params: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "limit": 1,
    }

    with Client(auth=("api", api_key)) as client:
        events_response = client.events.get(domain=domain, filters=params)
        print("GET Events (Sync):", events_response.json())

        items: list[dict[str, Any]] = events_response.json().get("items", [])
        if not items:
            print("No events found to resend.")
            return

        storage_url: str | None = items[0].get("storage", {}).get("url")
        if not storage_url:
            print("No storage URL found in event.")
            return

        resend_response = client.resendmessage.create(
            data=data,
            domain=domain,
            storage_url=storage_url,
        )
        print("Resend Message (Sync):", resend_response.json())


# ==============================================================================
# Message Management (Asynchronous)
# ==============================================================================


async def post_message_async(
    api_key: str,
    domain: str,
    from_email: str,
    to_email: str,
    cc_email: str,
    html_body: str,
    file_path_1: str,
    file_path_2: str,
) -> None:
    """
    POST /<domain>/messages (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tag": "Python test",
    }

    file_bytes_1: bytes = Path(file_path_1).read_bytes()
    file_bytes_2: bytes = Path(file_path_2).read_bytes()

    for file_content in (file_bytes_1, file_bytes_2):
        if len(file_content) > MAX_FILE_SIZE:
            raise UploadError("File too large")

    files: list[tuple[str, tuple[str, bytes]]] = [
        ("attachment", (Path(file_path_1).name, file_bytes_1)),
        ("attachment", (Path(file_path_2).name, file_bytes_2)),
    ]

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.messages.create(data=data, files=files, domain=domain)
        print("POST Message (Async):", response.json())


async def post_message_tags_async(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Message Tags (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tag": ["September newsletter", "newsletters"],
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.messages.create(data=data, domain=domain)
        print("POST Message Tags (Async):", response.json())


async def post_mime_async(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, mime_file_path: str
) -> None:
    """
    Mime messages
    POST /<domain>/messages.mime (Asynchronous)
    :return: None
    """
    mime_data: dict[str, str] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello HELLO",
    }
    files: dict[str, bytes] = {"message": Path(mime_file_path).read_bytes()}

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.mimemessage.create(data=mime_data, files=files, domain=domain)
        print("POST MIME (Async):", response.json())


async def post_no_tracking_async(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Message no tracking (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:tracking": False,
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.messages.create(data=data, domain=domain)
        print("POST No Tracking (Async):", response.json())


async def post_scheduled_async(
    api_key: str, domain: str, from_email: str, to_email: str, cc_email: str, html_body: str
) -> None:
    """
    Scheduled message (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "cc": cc_email,
        "subject": "Hello Vasyl Bodaj",
        "html": html_body,
        "o:deliverytime": "Thu Jan 28 2021 14:00:03 EST",
    }
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.messages.create(data=data, domain=domain)
        print("POST Scheduled (Async):", response.json())


async def resend_message_async(api_key: str, domain: str, from_email: str, to_email: str) -> None:
    """
    Resend message (Asynchronous)
    :return: None
    """
    data: dict[str, list[str]] = {"to": ["test1@example.com", "test2@example.com"]}
    params: dict[str, Any] = {
        "from": from_email,
        "to": to_email,
        "limit": 1,
    }

    async with AsyncClient(auth=("api", api_key)) as client:
        events_response = await client.events.get(domain=domain, filters=params)
        print("GET Events (Async):", events_response.json())

        items: list[dict[str, Any]] = events_response.json().get("items", [])
        if not items:
            print("No events found to resend.")
            return

        storage_url: str | None = items[0].get("storage", {}).get("url")
        if not storage_url:
            print("No storage URL found in event.")
            return

        resend_response = await client.resendmessage.create(
            data=data,
            domain=domain,
            storage_url=storage_url,
        )
        print("Resend Message (Async):", resend_response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")
    MESSAGES_FROM: str = os.environ.get("MESSAGES_FROM", "sender@example.com")
    MESSAGES_TO: str = os.environ.get("MESSAGES_TO", "recipient@example.com")
    MESSAGES_CC: str = os.environ.get("MESSAGES_CC", "cc@example.com")

    HTML_BODY: str = """<body style="margin: 0; padding: 0;">
     <table border="1" cellpadding="0" cellspacing="0" width="100%">
      <tr>
       <td>
        Hello!
       </td>
      </tr>
     </table>
    </body>"""

    # Dummy file paths mapped from the original logic for example execution
    FILE_PATH_1: str = "mailgun/doc_tests/files/test1.txt"
    FILE_PATH_2: str = "mailgun/doc_tests/files/test2.txt"
    MIME_FILE_PATH: str = "mailgun/doc_tests/files/test_mime.mime"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        # Pre-seed paths so missing files don't crash execution if paths don't exist
        Path("mailgun/doc_tests/files").mkdir(parents=True, exist_ok=True)
        if not Path(FILE_PATH_1).exists():
            Path(FILE_PATH_1).write_bytes(b"Test File 1 Bytes")
        if not Path(FILE_PATH_2).exists():
            Path(FILE_PATH_2).write_bytes(b"Test File 2 Bytes")
        if not Path(MIME_FILE_PATH).exists():
            Path(MIME_FILE_PATH).write_bytes(b"Content-Type: text/plain\n\nTest MIME")

        print("--- Running Synchronous Examples ---")
        post_message_sync(
            api_key=API_KEY,
            domain=DOMAIN,
            from_email=MESSAGES_FROM,
            to_email=MESSAGES_TO,
            cc_email=MESSAGES_CC,
            html_body=HTML_BODY,
            file_path_1=FILE_PATH_1,
            file_path_2=FILE_PATH_2,
        )
        # post_message_tags_sync(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO, cc_email=MESSAGES_CC, html_body=HTML_BODY)
        # post_mime_sync(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO, cc_email=MESSAGES_CC, mime_file_path=MIME_FILE_PATH)
        # post_no_tracking_sync(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO, cc_email=MESSAGES_CC, html_body=HTML_BODY)
        # post_scheduled_sync(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO, cc_email=MESSAGES_CC, html_body=HTML_BODY)
        # resend_message_sync(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO)

        print("\n--- Running Asynchronous Examples ---")
        # asyncio.run(post_message_async(api_key=API_KEY, domain=DOMAIN, from_email=MESSAGES_FROM, to_email=MESSAGES_TO, cc_email=MESSAGES_CC, html_body=HTML_BODY, file_path_1=FILE_PATH_1, file_path_2=FILE_PATH_2))

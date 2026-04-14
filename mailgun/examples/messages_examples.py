import os
from pathlib import Path

from mailgun.client import Client
from mailgun.handlers.error_handler import UploadError


# The maximum message size Mailgun supports is 25MB,
# see https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/send-http#send-via-http
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]
html: str = """<body style="margin: 0; padding: 0;">
 <table border="1" cellpadding="0" cellspacing="0" width="100%">
  <tr>
   <td>
    Hello!
   </td>
  </tr>
 </table>
</body>"""

client: Client = Client(auth=("api", key))


def post_message() -> None:
    # Messages
    # POST /<domain>/messages
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": html,
        "o:tag": "Python test",
    }
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.

    file_bytes_1 = Path("mailgun/doc_tests/files/test1.txt").read_bytes()
    file_bytes_2 = Path("mailgun/doc_tests/files/test2.txt").read_bytes()

    for file in {file_bytes_1, file_bytes_2}:
        if len(file) > MAX_FILE_SIZE:
            raise UploadError("File too large")

    files = [
        ("attachment", ("test1.txt", file_bytes_1)),
        ("attachment", ("test2.txt", file_bytes_2)),
    ]

    req = client.messages.create(data=data, files=files, domain=domain)
    print(req.json())


def post_mime() -> None:
    # Mime messages
    # POST /<domain>/messages.mime
    mime_data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello HELLO",
    }
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    # Mailgun requires the MIME string to be uploaded as a file
    # . Passing 'files' forces multipart/form-data.
    files = {"message": Path("mailgun/doc_tests/files/test_mime.mime").read_bytes()}

    req = client.mimemessage.create(data=mime_data, files=files, domain=domain)
    print(req.json())


def post_no_tracking() -> None:
    # Message no tracking
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": html,
        "o:tracking": False,
    }

    req = client.messages.create(data=data, domain=domain)
    print(req.json())


def post_scheduled() -> None:
    # Scheduled message
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": html,
        "o:deliverytime": "Thu Jan 28 2021 14:00:03 EST",
    }

    req = client.messages.create(data=data, domain=domain)
    print(req.json())


def post_message_tags() -> None:
    # Message Tags
    data = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "cc": os.environ["MESSAGES_CC"],
        "subject": "Hello Vasyl Bodaj",
        "html": html,
        "o:tag": ["September newsletter", "newsletters"],
    }

    req = client.messages.create(data=data, domain=domain)
    print(req.json())


def resend_message() -> None:
    data = {"to": ["test1@example.com", "test2@example.com"]}

    params = {
        "from": os.environ["MESSAGES_FROM"],
        "to": os.environ["MESSAGES_TO"],
        "limit": 1,
    }
    req_ev = client.events.get(domain=domain, filters=params)
    print(req_ev.json())

    req = client.resendmessage.create(
        data=data,
        domain=domain,
        storage_url=req_ev.json()["items"][0]["storage"]["url"],
    )
    print(req.json())


if __name__ == "__main__":
    post_message()

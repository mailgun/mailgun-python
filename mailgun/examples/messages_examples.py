import os
from pathlib import Path

from mailgun.client import Client


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
    files = [
        (
            "attachment",
            ("test1.txt", Path("mailgun/doc_tests/files/test1.txt").read_bytes()),
        ),
        (
            "attachment",
            ("test2.txt", Path("mailgun/doc_tests/files/test2.txt").read_bytes()),
        ),
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
    data = {"to": ["spidlisn@gmail.com", "mailgun@2048.zeefarmer.com"]}

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

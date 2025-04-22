import os
from pathlib import Path

from mailgun.client import Client


key: str = os.environ["APIKEY"]
domain: str = os.environ["DOMAIN"]

client: Client = Client(auth=("api", key))


def get_single_validate() -> None:
    """
    GET /v4/address/validate
    :return:
    """
    params = {"address": "test@gmail.com", "provider_lookup": "false"}
    req = client.addressvalidate.get(domain=domain, filters=params)
    print(req.json())


def post_single_validate() -> None:
    """
    POST /v4/address/validate
    :return:
    """
    data = {"address": "test2@gmail.com"}
    params = {"provider_lookup": "false"}
    req = client.addressvalidate.create(domain=domain, data=data, filters=params)
    print(req.json())


def get_bulk_validate() -> None:
    """
    GET /v4/address/validate/bulk
    :return:
    """
    params = {"limit": 2}
    req = client.addressvalidate_bulk.get(domain=domain, filters=params)
    print(req.json())


def post_bulk_list_validate() -> None:
    """
    POST /v4/address/validate/bulk/<list_id>
    :return:
    """
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    files = {"file": Path("mailgun/doc_tests/files/email_validation.csv").read_bytes()}
    req = client.addressvalidate_bulk.create(
        domain=domain, files=files, list_name="python2_list"
    )
    print(req.json())


def get_bulk_list_validate() -> None:
    """
    GET /v4/address/validate/bulk/<list_id>
    :return:
    """
    req = client.addressvalidate_bulk.get(domain=domain, list_name="python2_list")
    print(req.json())


def delete_bulk_list_validate() -> None:
    """
    DELETE /v4/address/validate/bulk/<list_id>
    :return:
    """
    req = client.addressvalidate_bulk.delete(domain=domain, list_name="python2_list")
    print(req.json())


def get_preview() -> None:
    """
    GET /v4/address/validate/preview
    :return:
    """
    req = client.addressvalidate_preview.get(domain=domain)
    print(req.json())


def post_preview() -> None:
    """
    POST /v4/address/validate/preview/<list_id>
    :return:
    """
    # It is strongly recommended that you open files in binary mode.
    # Because the Content-Length header may be provided for you,
    # and if it does this value will be set to the number of bytes in the file.
    # Errors may occur if you open the file in text mode.
    files = {"file": Path("mailgun/doc_tests/files/email_previews.csv").read_bytes()}
    req = client.addressvalidate_preview.create(
        domain=domain, files=files, list_name="python_list"
    )
    print(req.json())


def delete_preview() -> None:
    """
    DELETE /v4/address/validate/preview/<list_id>
    :return:
    """
    req = client.addressvalidate_preview.delete(domain=domain, list_name="python_list")
    print(req.text)


if __name__ == "__main__":
    delete_preview()

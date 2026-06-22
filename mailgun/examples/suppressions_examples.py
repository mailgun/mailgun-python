"""Examples for managing Mailgun Suppressions (Bounces, Unsubscribes, Complaints, Whitelists)."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import UploadError


# The maximum message size Mailgun supports is 25MB
MAX_FILE_SIZE: int = 25 * 1024 * 1024


# ==============================================================================
# Suppressions: Bounces (Synchronous)
# ==============================================================================


def delete_all_bounces_sync(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/bounces
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.bounces.delete(domain=domain)
        print("DELETE All Bounces (Sync):", response.json())


def delete_single_bounce_sync(api_key: str, domain: str, bounce_address: str) -> None:
    """
    DELETE /<domain>/bounces/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.bounces.delete(domain=domain, bounce_address=bounce_address)
        print("DELETE Single Bounce (Sync):", response.json())


def get_bounces_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/bounces
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.bounces.get(domain=domain)
        print("GET Bounces (Sync):", response.json())


def get_single_bounce_sync(api_key: str, domain: str, bounce_address: str) -> None:
    """
    GET /<domain>/bounces/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.bounces.get(domain=domain, bounce_address=bounce_address)
        print("GET Single Bounce (Sync):", response.json())


def import_bounces_sync(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/bounces/import, Content-Type: multipart/form-data
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    if csv_filepath.stat().st_size > MAX_FILE_SIZE:
        raise UploadError(f"File too large and exceeds the limit of {MAX_FILE_SIZE}")

    csv_data: bytes = csv_filepath.read_bytes()
    if not csv_data:
        raise ValueError("File is empty.")

    files: dict[str, bytes] = {"file": csv_data}
    with Client(auth=("api", api_key)) as client:
        response = client.bounces_import.create(domain=domain, files=files)
        print("Import Bounces (Sync):", response.json())


def post_bounce_sync(api_key: str, domain: str, bounce_address: str) -> None:
    """
    POST /<domain>/bounces
    :return: None
    """
    data: dict[str, Any] = {"address": bounce_address, "code": 550, "error": "Test error"}
    with Client(auth=("api", api_key)) as client:
        response = client.bounces.create(data=data, domain=domain)
        print("POST Bounce (Sync):", response.json())


def post_multiple_bounces_sync(api_key: str, domain: str) -> None:
    """
    POST /<domain>/bounces, Content-Type: application/json
    :return: None
    """
    data: str = """[{
        "address": "test121@i.ua",
        "code": "550",
        "error": "Test error2312"
    },
    {
        "address": "test122@gmail.com",
        "code": "550",
        "error": "Test error"
    }]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    with Client(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = client.bounces.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Bounces (Sync):", response.json())


# ==============================================================================
# Suppressions: Complaints (Synchronous)
# ==============================================================================


def delete_all_complaints_sync(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/complaints/
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.complaints.delete(domain=domain)
        print("DELETE All Complaints (Sync):", response.json())


def delete_single_complaint_sync(api_key: str, domain: str, complaint_address: str) -> None:
    """
    DELETE /<domain>/complaints/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.complaints.delete(domain=domain, complaint_address=complaint_address)
        print("DELETE Single Complaint (Sync):", response.json())


def get_complaints_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/complaints
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.complaints.get(domain=domain)
        print("GET Complaints (Sync):", response.json())


def get_single_complaint_sync(api_key: str, domain: str, complaint_address: str) -> None:
    """
    GET /<domain>/complaints/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.complaints.get(domain=domain, complaint_address=complaint_address)
        print("GET Single Complaint (Sync):", response.json())


def import_complaints_sync(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/complaints/import, Content-Type: multipart/form-data
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"complaints_csv": csv_filepath.read_bytes()}
    with Client(auth=("api", api_key)) as client:
        response = client.complaints_import.create(domain=domain, files=files)
        print("Import Complaints (Sync):", response.json())


def post_complaint_sync(api_key: str, domain: str, complaint_address: str) -> None:
    """
    POST /<domain>/complaints
    :return: None
    """
    data: dict[str, Any] = {"address": complaint_address, "tag": "compl_test_tag"}
    with Client(auth=("api", api_key)) as client:
        response = client.complaints.create(data=data, domain=domain)
        print("POST Complaint (Sync):", response.json())


def post_multiple_complaints_sync(api_key: str, domain: str) -> None:
    """
    POST /<domain>/complaints, Content-Type: application/json
    :return: None
    """
    data: str = """[{
        "address": "alice1@example.com",
        "tags": ["some tag"],
        "created_at": "Thu, 13 Oct 2011 18:02:00 UTC"
    },
    {"address": "carol1@example.com"}]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    with Client(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = client.complaints.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Complaints (Sync):", response.json())


# ==============================================================================
# Suppressions: Unsubscribes (Synchronous)
# ==============================================================================


def delete_all_unsubscribes_sync(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/unsubscribes/
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes.delete(domain=domain)
        print("DELETE All Unsubscribes (Sync):", response.json())


def delete_single_unsubscribe_sync(api_key: str, domain: str, unsubscribe_address: str) -> None:
    """
    DELETE /<domain>/unsubscribes/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes.delete(
            domain=domain, unsubscribe_address=unsubscribe_address
        )
        print("DELETE Single Unsubscribe (Sync):", response.json())


def get_single_unsubscribe_sync(api_key: str, domain: str, unsubscribe_address: str) -> None:
    """
    GET /<domain>/unsubscribes/<address>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes.get(domain=domain, unsubscribe_address=unsubscribe_address)
        print("GET Single Unsubscribe (Sync):", response.json())


def get_unsubscribes_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/unsubscribes
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes.get(domain=domain)
        print("GET Unsubscribes (Sync):", response.json())


def import_unsubscribes_sync(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/unsubscribes/import, Content-Type: multipart/form-data
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"unsubscribe_csv": csv_filepath.read_bytes()}
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes_import.create(domain=domain, files=files)
        print("Import Unsubscribes (Sync):", response.json())


def post_multiple_unsubscribes_sync(api_key: str, domain: str) -> None:
    """
    POST /<domain>/unsubscribes, Content-Type: application/json
    :return: None
    """
    data: str = """[{
        "address": "alice@example.com",
        "tags": ["some tag"],
        "created_at": "Thu, 13 Oct 2011 18:02:00 UTC"
    },
    {
        "address": "bob@example.com",
        "tags": ["*"]
    },
    {"address": "carol@example.com"}]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    with Client(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = client.unsubscribes.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Unsubscribes (Sync):", response.json())


def post_unsubscribe_sync(api_key: str, domain: str, unsubscribe_address: str) -> None:
    """
    POST /<domain>/unsubscribes
    :return: None
    """
    data: dict[str, Any] = {"address": unsubscribe_address, "tag": "*"}
    with Client(auth=("api", api_key)) as client:
        response = client.unsubscribes.create(data=data, domain=domain)
        print("POST Unsubscribe (Sync):", response.json())


# ==============================================================================
# Suppressions: Whitelists (Synchronous)
# ==============================================================================


def delete_all_whitelists_sync(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/whitelists
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists.delete(domain=domain)
        print("DELETE All Whitelists (Sync):", response.json())


def delete_single_whitelist_sync(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    DELETE /<domain>/whitelists/<address or domain>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists.delete(domain=domain, whitelist_address=whitelist_address)
        print("DELETE Single Whitelist (Sync):", response.json())


def get_single_whitelist_sync(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    GET /<domain>/whitelists/<address or domain>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists.get(domain=domain, whitelist_address=whitelist_address)
        print("GET Single Whitelist (Sync):", response.json())


def get_whitelists_sync(api_key: str, domain: str) -> None:
    """
    GET /<domain>/whitelists
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists.get(domain=domain)
        print("GET Whitelists (Sync):", response.json())


def import_whitelists_sync(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/whitelists/import, Content-Type: multipart/form-data
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"whitelist_csv": csv_filepath.read_bytes()}
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists_import.create(domain=domain, files=files)
        print("Import Whitelists (Sync):", response.json())


def post_whitelist_sync(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    POST /<domain>/whitelists
    :return: None
    """
    data: dict[str, Any] = {"address": whitelist_address, "tag": "whitel_test"}
    with Client(auth=("api", api_key)) as client:
        response = client.whitelists.create(data=data, domain=domain)
        print("POST Whitelist (Sync):", response.json())


# ==============================================================================
# Suppressions: Bounces (Asynchronous)
# ==============================================================================


async def delete_all_bounces_async(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/bounces (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces.delete(domain=domain)
        print("DELETE All Bounces (Async):", response.json())


async def delete_single_bounce_async(api_key: str, domain: str, bounce_address: str) -> None:
    """
    DELETE /<domain>/bounces/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces.delete(domain=domain, bounce_address=bounce_address)
        print("DELETE Single Bounce (Async):", response.json())


async def get_bounces_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/bounces (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces.get(domain=domain)
        print("GET Bounces (Async):", response.json())


async def get_single_bounce_async(api_key: str, domain: str, bounce_address: str) -> None:
    """
    GET /<domain>/bounces/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces.get(domain=domain, bounce_address=bounce_address)
        print("GET Single Bounce (Async):", response.json())


async def import_bounces_async(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/bounces/import (Asynchronous)
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    csv_data: bytes = csv_filepath.read_bytes()
    if not csv_data:
        raise ValueError("File is empty.")

    files: dict[str, bytes] = {"file": csv_data}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces_import.create(domain=domain, files=files)
        print("Import Bounces (Async):", response.json())


async def post_bounce_async(api_key: str, domain: str, bounce_address: str) -> None:
    """
    POST /<domain>/bounces (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"address": bounce_address, "code": 550, "error": "Test error"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.bounces.create(data=data, domain=domain)
        print("POST Bounce (Async):", response.json())


async def post_multiple_bounces_async(api_key: str, domain: str) -> None:
    """
    POST /<domain>/bounces, Content-Type: application/json (Asynchronous)
    :return: None
    """
    data: str = """[{
        "address": "test121@i.ua",
        "code": "550",
        "error": "Test error2312"
    },
    {
        "address": "test122@gmail.com",
        "code": "550",
        "error": "Test error"
    }]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    async with AsyncClient(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = await client.bounces.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Bounces (Async):", response.json())


# ==============================================================================
# Suppressions: Complaints (Asynchronous)
# ==============================================================================


async def delete_all_complaints_async(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/complaints/ (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints.delete(domain=domain)
        print("DELETE All Complaints (Async):", response.json())


async def delete_single_complaint_async(api_key: str, domain: str, complaint_address: str) -> None:
    """
    DELETE /<domain>/complaints/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints.delete(
            domain=domain, complaint_address=complaint_address
        )
        print("DELETE Single Complaint (Async):", response.json())


async def get_complaints_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/complaints (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints.get(domain=domain)
        print("GET Complaints (Async):", response.json())


async def get_single_complaint_async(api_key: str, domain: str, complaint_address: str) -> None:
    """
    GET /<domain>/complaints/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints.get(domain=domain, complaint_address=complaint_address)
        print("GET Single Complaint (Async):", response.json())


async def import_complaints_async(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/complaints/import (Asynchronous)
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"complaints_csv": csv_filepath.read_bytes()}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints_import.create(domain=domain, files=files)
        print("Import Complaints (Async):", response.json())


async def post_complaint_async(api_key: str, domain: str, complaint_address: str) -> None:
    """
    POST /<domain>/complaints (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"address": complaint_address, "tag": "compl_test_tag"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.complaints.create(data=data, domain=domain)
        print("POST Complaint (Async):", response.json())


async def post_multiple_complaints_async(api_key: str, domain: str) -> None:
    """
    POST /<domain>/complaints, Content-Type: application/json (Asynchronous)
    :return: None
    """
    data: str = """[{
        "address": "alice1@example.com",
        "tags": ["some tag"],
        "created_at": "Thu, 13 Oct 2011 18:02:00 UTC"
    },
    {"address": "carol1@example.com"}]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    async with AsyncClient(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = await client.complaints.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Complaints (Async):", response.json())


# ==============================================================================
# Suppressions: Unsubscribes (Asynchronous)
# ==============================================================================


async def delete_all_unsubscribes_async(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/unsubscribes/ (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes.delete(domain=domain)
        print("DELETE All Unsubscribes (Async):", response.json())


async def delete_single_unsubscribe_async(
    api_key: str, domain: str, unsubscribe_address: str
) -> None:
    """
    DELETE /<domain>/unsubscribes/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes.delete(
            domain=domain, unsubscribe_address=unsubscribe_address
        )
        print("DELETE Single Unsubscribe (Async):", response.json())


async def get_single_unsubscribe_async(api_key: str, domain: str, unsubscribe_address: str) -> None:
    """
    GET /<domain>/unsubscribes/<address> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes.get(
            domain=domain, unsubscribe_address=unsubscribe_address
        )
        print("GET Single Unsubscribe (Async):", response.json())


async def get_unsubscribes_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/unsubscribes (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes.get(domain=domain)
        print("GET Unsubscribes (Async):", response.json())


async def import_unsubscribes_async(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/unsubscribes/import (Asynchronous)
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"unsubscribe_csv": csv_filepath.read_bytes()}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes_import.create(domain=domain, files=files)
        print("Import Unsubscribes (Async):", response.json())


async def post_multiple_unsubscribes_async(api_key: str, domain: str) -> None:
    """
    POST /<domain>/unsubscribes, Content-Type: application/json (Asynchronous)
    :return: None
    """
    data: str = """[{
        "address": "alice@example.com",
        "tags": ["some tag"],
        "created_at": "Thu, 13 Oct 2011 18:02:00 UTC"
    },
    {
        "address": "bob@example.com",
        "tags": ["*"]
    },
    {"address": "carol@example.com"}]"""
    json_data: list[dict[str, Any]] = json.loads(data)
    async with AsyncClient(auth=("api", api_key)) as client:
        for address_data in json_data:
            response = await client.unsubscribes.create(
                data=address_data, domain=domain, headers={"Content-Type": "application/json"}
            )
            print("POST Multiple Unsubscribes (Async):", response.json())


async def post_unsubscribe_async(api_key: str, domain: str, unsubscribe_address: str) -> None:
    """
    POST /<domain>/unsubscribes (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"address": unsubscribe_address, "tag": "*"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.unsubscribes.create(data=data, domain=domain)
        print("POST Unsubscribe (Async):", response.json())


# ==============================================================================
# Suppressions: Whitelists (Asynchronous)
# ==============================================================================


async def delete_all_whitelists_async(api_key: str, domain: str) -> None:
    """
    DELETE /<domain>/whitelists (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists.delete(domain=domain)
        print("DELETE All Whitelists (Async):", response.json())


async def delete_single_whitelist_async(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    DELETE /<domain>/whitelists/<address or domain> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists.delete(
            domain=domain, whitelist_address=whitelist_address
        )
        print("DELETE Single Whitelist (Async):", response.json())


async def get_single_whitelist_async(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    GET /<domain>/whitelists/<address or domain> (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists.get(domain=domain, whitelist_address=whitelist_address)
        print("GET Single Whitelist (Async):", response.json())


async def get_whitelists_async(api_key: str, domain: str) -> None:
    """
    GET /<domain>/whitelists (Asynchronous)
    :return: None
    """
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists.get(domain=domain)
        print("GET Whitelists (Async):", response.json())


async def import_whitelists_async(api_key: str, domain: str, file_path: str) -> None:
    """
    POST /<domain>/whitelists/import (Asynchronous)
    :return: None
    """
    csv_filepath = Path(file_path)
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping import.")
        return

    files: dict[str, bytes] = {"whitelist_csv": csv_filepath.read_bytes()}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists_import.create(domain=domain, files=files)
        print("Import Whitelists (Async):", response.json())


async def post_whitelist_async(api_key: str, domain: str, whitelist_address: str) -> None:
    """
    POST /<domain>/whitelists (Asynchronous)
    :return: None
    """
    data: dict[str, Any] = {"address": whitelist_address, "tag": "whitel_test"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.whitelists.create(data=data, domain=domain)
        print("POST Whitelist (Async):", response.json())


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")
    DOMAIN: str = os.environ.get("DOMAIN", "")

    # Identifiers mapping to your original business logic
    BOUNCE_ADDR: str = "foo@example.com"
    UNSUB_ADDR: str = "bar@example.com"
    COMPLAINT_ADDR: str = "bob@example.com"
    WHITELIST_ADDR: str = "test@example.com"

    # Dummy file paths extracted from original logic
    BOUNCES_FILE: str = "mailgun/doc_tests/files/mailgun_bounces_test.csv"
    UNSUBS_FILE: str = "mailgun/doc_tests/files/mailgun_unsubscribes.csv"
    COMPLAINTS_FILE: str = "mailgun/doc_tests/files/mailgun_complaints.csv"
    WHITELISTS_FILE: str = "mailgun/doc_tests/files/mailgun_whitelists.csv"

    if not API_KEY or not DOMAIN:
        print("Please set the 'APIKEY' and 'DOMAIN' environment variables to run examples.")
    else:
        # Pre-seed paths so missing files don't crash execution if paths don't exist locally
        Path("mailgun/doc_tests/files").mkdir(parents=True, exist_ok=True)
        for filepath in (BOUNCES_FILE, UNSUBS_FILE, COMPLAINTS_FILE, WHITELISTS_FILE):
            if not Path(filepath).exists():
                Path(filepath).write_bytes(b"address,code,error\nplaceholder@example.com,550,test")

        print("--- Running Synchronous Examples ---")
        import_bounces_sync(api_key=API_KEY, domain=DOMAIN, file_path=BOUNCES_FILE)
        delete_single_whitelist_sync(
            api_key=API_KEY, domain=DOMAIN, whitelist_address=WHITELIST_ADDR
        )

        # Other Sync operations you may uncomment to test:
        # post_bounce_sync(api_key=API_KEY, domain=DOMAIN, bounce_address=BOUNCE_ADDR)
        # get_bounces_sync(api_key=API_KEY, domain=DOMAIN)
        # delete_all_bounces_sync(api_key=API_KEY, domain=DOMAIN)
        # post_complaint_sync(api_key=API_KEY, domain=DOMAIN, complaint_address=COMPLAINT_ADDR)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(import_bounces_async(api_key=API_KEY, domain=DOMAIN, file_path=BOUNCES_FILE))
        asyncio.run(
            delete_single_whitelist_async(
                api_key=API_KEY, domain=DOMAIN, whitelist_address=WHITELIST_ADDR
            )
        )

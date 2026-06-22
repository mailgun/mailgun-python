"""Examples for Mailgun Address Validation API."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from mailgun.client import AsyncClient, Client
from mailgun.handlers.error_handler import UploadError


# The maximum message size Mailgun supports is 25MB
MAX_FILE_SIZE: int = 25 * 1024 * 1024


def _print_response(prefix: str, response: Any) -> None:
    """Helper to safely print response JSON, falling back to raw text on Free/Sandbox errors."""
    try:
        print(f"{prefix}:", response.json())
    except Exception:
        print(f"{prefix}: HTTP {response.status_code} - {response.text}")


# ==============================================================================
# Single Validation Examples
# ==============================================================================


def get_single_validate_sync(api_key: str) -> None:
    """
    GET /v4/address/validate
    :return: None
    """
    params: dict[str, str] = {"address": "test@gmail.com", "provider_lookup": "false"}
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate.get(filters=params)
        _print_response("GET Single Validate (Sync)", response)


def post_single_validate_sync(api_key: str) -> None:
    """
    POST /v4/address/validate
    :return: None
    """
    data: dict[str, str] = {"address": "test2@gmail.com"}
    params: dict[str, str] = {"provider_lookup": "false"}
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate.create(data=data, filters=params)
        _print_response("POST Single Validate (Sync)", response)


async def post_single_validate_async(api_key: str) -> None:
    """
    POST /v4/address/validate (Asynchronous)
    :return: None
    """
    data: dict[str, str] = {"address": "test_async@gmail.com"}
    params: dict[str, str] = {"provider_lookup": "false"}
    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.addressvalidate.create(data=data, filters=params)
        _print_response("POST Single Validate (Async)", response)


# ==============================================================================
# Bulk List Validation Examples
# ==============================================================================


def delete_bulk_list_validate_sync(api_key: str) -> None:
    """
    DELETE /v4/address/validate/bulk/<list_id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_bulk.delete(list_name="python2_list")
        _print_response("DELETE Bulk List Validate (Sync)", response)


def get_bulk_list_validate_sync(api_key: str) -> None:
    """
    GET /v4/address/validate/bulk/<list_id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_bulk.get(list_name="python2_list")
        _print_response("GET Specific Bulk List Validate (Sync)", response)


def get_bulk_validate_sync(api_key: str) -> None:
    """
    GET /v4/address/validate/bulk
    :return: None
    """
    params: dict[str, int] = {"limit": 2}
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_bulk.get(filters=params)
        _print_response("GET Bulk Validate (Sync)", response)


def post_bulk_list_validate_sync(api_key: str, csv_filepath: Path) -> None:
    """
    POST /v4/address/validate/bulk/<list_id>
    :return: None
    """
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping bulk validation upload.")
        return

    if csv_filepath.stat().st_size > MAX_FILE_SIZE:
        raise UploadError(f"File too large and exceeds the limit of {MAX_FILE_SIZE} bytes")

    csv_data: bytes = csv_filepath.read_bytes()

    if not csv_data:
        raise ValueError("File is empty.")

    # Using the tuple format ensures requests/httpx correctly flags multipart/form-data
    files: dict[str, tuple[str, bytes, str]] = {"file": (csv_filepath.name, csv_data, "text/csv")}

    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_bulk.create(files=files, list_name="python2_list")
        _print_response("POST Bulk List Validate (Sync)", response)


async def post_bulk_list_validate_async(api_key: str, csv_filepath: Path) -> None:
    """
    POST /v4/address/validate/bulk/<list_id> (Asynchronous)
    :return: None
    """
    if not csv_filepath.exists():
        return

    csv_data: bytes = csv_filepath.read_bytes()
    files: dict[str, tuple[str, bytes, str]] = {"file": (csv_filepath.name, csv_data, "text/csv")}

    async with AsyncClient(auth=("api", api_key)) as client:
        response = await client.addressvalidate_bulk.create(
            files=files, list_name="async_python_list"
        )
        _print_response("POST Bulk List Validate (Async)", response)


# ==============================================================================
# Validation Preview Examples
# ==============================================================================


def delete_preview_sync(api_key: str) -> None:
    """
    DELETE /v4/address/validate/preview/<list_id>
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_preview.delete(list_name="python_list")
        _print_response("DELETE Preview (Sync)", response)


def get_preview_sync(api_key: str) -> None:
    """
    GET /v4/address/validate/preview
    :return: None
    """
    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_preview.get()
        _print_response("GET Preview (Sync)", response)


def post_preview_sync(api_key: str, csv_filepath: Path) -> None:
    """
    POST /v4/address/validate/preview/<list_id>
    :return: None
    """
    if not csv_filepath.exists():
        print(f"File {csv_filepath} not found. Skipping preview upload.")
        return

    csv_data: bytes = csv_filepath.read_bytes()
    files: dict[str, tuple[str, bytes, str]] = {"file": (csv_filepath.name, csv_data, "text/csv")}

    with Client(auth=("api", api_key)) as client:
        response = client.addressvalidate_preview.create(files=files, list_name="python_list")
        _print_response("POST Preview (Sync)", response)


# ==============================================================================
# Execution
# ==============================================================================

if __name__ == "__main__":
    # Securely load environment variables at runtime
    API_KEY: str = os.environ.get("APIKEY", "")

    # Define target files
    VALIDATION_CSV = Path("mailgun/doc_tests/files/email_validation.csv")
    PREVIEW_CSV = Path("mailgun/doc_tests/files/email_previews.csv")

    if not API_KEY:
        print("Please set the 'APIKEY' environment variable to run examples.")
    else:
        # Pre-seed files so the script doesn't crash on the first run if the directory is missing
        VALIDATION_CSV.parent.mkdir(parents=True, exist_ok=True)
        if not VALIDATION_CSV.exists():
            VALIDATION_CSV.write_bytes(b"email\ntest1@example.com\n")
        if not PREVIEW_CSV.exists():
            PREVIEW_CSV.write_bytes(b"email\npreview1@example.com\n")

        print("--- Running Synchronous Examples ---")
        get_single_validate_sync(api_key=API_KEY)
        post_single_validate_sync(api_key=API_KEY)

        get_bulk_validate_sync(api_key=API_KEY)
        post_bulk_list_validate_sync(api_key=API_KEY, csv_filepath=VALIDATION_CSV)
        get_bulk_list_validate_sync(api_key=API_KEY)
        # delete_bulk_list_validate_sync(api_key=API_KEY, domain=DOMAIN)

        get_preview_sync(api_key=API_KEY)
        post_preview_sync(api_key=API_KEY, csv_filepath=PREVIEW_CSV)
        # delete_preview_sync(api_key=API_KEY, domain=DOMAIN)

        print("\n--- Running Asynchronous Examples ---")
        asyncio.run(post_single_validate_async(api_key=API_KEY))
        asyncio.run(post_bulk_list_validate_async(api_key=API_KEY, csv_filepath=VALIDATION_CSV))

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mailgun.endpoints import AsyncEndpoint, Endpoint


class MockResponse:
    """A lightweight mock for HTTPX / Requests responses."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ValueError(f"HTTP Error: {self.status_code}")


class TestStreamPaginationAsync:
    @patch.object(AsyncEndpoint, "get", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_async_stream_pagination_traverses_pages(
        self, mock_async_get: AsyncMock
    ) -> None:
        page_1 = MockResponse(
            {
                "items": [{"id": "async_1"}],
                "paging": {"next": "https://api.mailgun.net/v3/domains?skip=1"},
            }
        )
        page_2 = MockResponse(
            {
                "items": [],
                "paging": {"next": "https://api.mailgun.net/v3/domains?skip=2"},
            }
        )
        mock_async_get.side_effect = [page_1, page_2]

        async_endpoint = AsyncEndpoint(
            url={"base": "http://mock", "keys": []},
            headers={},
            auth=None,
            client=MagicMock(),
        )

        results = [item async for item in async_endpoint.stream()]  # pyright: ignore[reportGeneralTypeIssues]

        assert mock_async_get.call_count == 2
        assert results == [{"id": "async_1"}]
        mock_async_get.assert_any_call(domain=None, filters={"skip": "1"})


class TestStreamPaginationErrorHandling:
    @patch.object(Endpoint, "get")
    def test_stream_respects_raise_for_status_errors(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MockResponse({}, status_code=401)
        endpoint = Endpoint(
            url={"base": "http://mock", "keys": []}, headers={}, auth=None
        )

        with pytest.raises(ValueError, match="HTTP Error: 401"):
            list(endpoint.stream())


class TestStreamPaginationSync:
    @patch.object(Endpoint, "get")
    def test_sync_stream_pagination_traverses_pages(self, mock_get: MagicMock) -> None:
        page_1 = MockResponse(
            {
                "items": [{"id": "event_1"}, {"id": "event_2"}],
                "paging": {
                    "next": (
                        "https://api.mailgun.net/v3/events"
                        "?event=delivered&page=next_page&limit=2"
                    )
                },
            }
        )
        page_2 = MockResponse({"items": [{"id": "event_3"}], "paging": {}})
        mock_get.side_effect = [page_1, page_2]

        endpoint = Endpoint(
            url={"base": "http://mock", "keys": []}, headers={}, auth=None
        )

        results = list(endpoint.stream(filters={"event": "delivered"}))

        assert mock_get.call_count == 2
        assert results == [{"id": "event_1"}, {"id": "event_2"}, {"id": "event_3"}]
        mock_get.assert_any_call(domain=None, filters={"event": "delivered"})
        mock_get.assert_any_call(
            domain=None,
            filters={"event": "delivered", "limit": "2", "page": "next_page"},
        )

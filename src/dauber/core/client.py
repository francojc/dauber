"""Async HTTP client for the Canvas LMS API."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode

import httpx

from dauber.core.config import Config

MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds


class CanvasClient:
    """Async HTTP client wrapping httpx for Canvas API requests."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.canvas_api_url,
            headers={
                "Authorization": f"Bearer {config.canvas_api_key}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(config.api_timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        form_data: dict[str, str] | list[tuple[str, str]] | None = None,
    ) -> Any:
        """Make an authenticated Canvas API request with retry on 429.

        Args:
            method: HTTP method (get, post, put, delete).
            endpoint: API path relative to base URL (e.g., "/courses").
            params: Query parameters.
            data: JSON body for POST/PUT.
            form_data: URL-encoded form body. Use a list of tuples
                when keys repeat (e.g., bracket-notation rubric data).

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
        """
        for attempt in range(MAX_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {}
                if params:
                    kwargs["params"] = params
                if data is not None:
                    kwargs["json"] = data
                if form_data is not None:
                    if isinstance(form_data, list):
                        kwargs["content"] = urlencode(form_data)
                        kwargs["headers"] = {
                            "Content-Type": ("application/x-www-form-urlencoded"),
                        }
                    else:
                        kwargs["data"] = form_data

                response = await self._client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                if response.status_code == 204:
                    return {}
                return response.json()

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < MAX_RETRIES:
                    retry_after = exc.response.headers.get("Retry-After")
                    wait = (
                        int(retry_after)
                        if retry_after
                        else INITIAL_BACKOFF * (2**attempt)
                    )
                    await asyncio.sleep(wait)
                    continue
                raise

    async def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of a paginated Canvas API endpoint.

        Uses page/per_page query parameters. Stops when a page returns
        fewer results than per_page.
        """
        params = dict(params) if params else {}
        params["per_page"] = per_page
        all_results: list[dict[str, Any]] = []
        page = 1

        while True:
            page_params = {**params, "page": page}
            response = await self.request("get", endpoint, params=page_params)
            if not response:
                break
            if isinstance(response, list):
                all_results.extend(response)
                if len(response) < per_page:
                    break
            else:
                all_results.append(response)
                break
            page += 1

        return all_results

    async def download(self, url: str) -> bytes:
        """Download a binary resource from an absolute URL.

        Uses the same auth headers as the rest of the client.
        Follows redirects so Canvas file attachments (which redirect
        to pre-signed S3 URLs) are fetched correctly.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        response = await self._client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content

    async def test_connection(self) -> tuple[bool, str]:
        """Test the Canvas API connection and token validity.

        Returns:
            Tuple of (success, message).
        """
        try:
            user = await self.request("get", "/users/self")
            name = user.get("name", "Unknown")
            return True, f"Connected as {name}"
        except httpx.HTTPStatusError as exc:
            return False, f"HTTP {exc.response.status_code}: {exc.response.text}"
        except httpx.ConnectError:
            return False, f"Cannot reach {self._config.canvas_base_url}"

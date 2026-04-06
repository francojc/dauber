"""Lazy initialization of Config, CanvasClient, and CourseCache."""

from __future__ import annotations

from typing import Any

from dauber.core.cache import CourseCache
from dauber.core.client import CanvasClient
from dauber.core.config import Config


class EaselContext:
    """Holds lazily-initialized core objects for CLI commands.

    Stored on ``typer.Context.obj["ctx"]`` by the app callback.
    """

    def __init__(self) -> None:
        self._config: Config | None = None
        self._client: CanvasClient | None = None
        self._cache: CourseCache | None = None

    @property
    def config(self) -> Config:
        if self._config is None:
            self._config = Config()
            self._config.validate_config()
        return self._config

    @property
    def client(self) -> CanvasClient:
        if self._client is None:
            self._client = CanvasClient(self.config)
        return self._client

    @property
    def cache(self) -> CourseCache:
        if self._cache is None:
            self._cache = CourseCache(self.client)
        return self._cache

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()


def get_context(ctx_obj: dict[str, Any]) -> EaselContext:
    """Retrieve or create the EaselContext from a Typer context dict."""
    if "ctx" not in ctx_obj:
        ctx_obj["ctx"] = EaselContext()
    return ctx_obj["ctx"]

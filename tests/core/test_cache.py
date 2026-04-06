"""Tests for dauber.core.cache."""

from unittest.mock import AsyncMock

import pytest

from dauber.core.cache import CourseCache


@pytest.fixture()
def mock_client():
    client = AsyncMock()
    client.get_paginated = AsyncMock(
        return_value=[
            {"id": 101, "course_code": "IS505"},
            {"id": 202, "course_code": "LING400"},
        ]
    )
    return client


@pytest.fixture()
def cache(mock_client):
    return CourseCache(mock_client)


async def test_resolve_numeric_passthrough(cache, mock_client):
    result = await cache.resolve("12345")
    assert result == "12345"
    mock_client.get_paginated.assert_not_called()


async def test_resolve_sis_passthrough(cache, mock_client):
    result = await cache.resolve("sis_course_id:IS505")
    assert result == "sis_course_id:IS505"
    mock_client.get_paginated.assert_not_called()


async def test_resolve_code_triggers_refresh(cache, mock_client):
    result = await cache.resolve("IS505")
    assert result == "101"
    mock_client.get_paginated.assert_called_once()


async def test_resolve_code_uses_cache(cache, mock_client):
    await cache.refresh()
    mock_client.get_paginated.reset_mock()
    result = await cache.resolve("IS505")
    assert result == "101"
    mock_client.get_paginated.assert_not_called()


async def test_resolve_unknown_code_falls_back_to_sis(cache, mock_client):
    result = await cache.resolve("UNKNOWN999")
    assert result == "sis_course_id:UNKNOWN999"


async def test_refresh_populates_both_maps(cache, mock_client):
    await cache.refresh()
    assert cache.get_id("IS505") == "101"
    assert cache.get_id("LING400") == "202"
    assert cache.get_code(101) == "IS505"
    assert cache.get_code(202) == "LING400"


async def test_get_code_unknown_returns_none(cache):
    assert cache.get_code("99999") is None


async def test_get_id_unknown_returns_none(cache):
    assert cache.get_id("NOPE") is None


async def test_resolve_int_passthrough(cache, mock_client):
    result = await cache.resolve(12345)
    assert result == "12345"
    mock_client.get_paginated.assert_not_called()

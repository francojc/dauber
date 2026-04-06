"""Shared test fixtures for dauber."""

import pytest

from dauber.core.config import Config


@pytest.fixture()
def config():
    """Config with a fake token for testing."""
    return Config(
        canvas_api_key="fake-test-token",
        canvas_base_url="https://canvas.test",
    )

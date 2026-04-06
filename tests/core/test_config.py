"""Tests for dauber.core.config."""

import pytest

from dauber.core.config import Config


def test_defaults(monkeypatch):
    """Config loads with defaults when env vars are empty."""
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    cfg = Config(canvas_api_key="test-token")
    assert cfg.canvas_base_url == "https://canvas.illinois.edu"
    assert cfg.api_timeout == 30
    assert cfg.cache_ttl == 300


def test_trailing_slash_stripped():
    cfg = Config(
        canvas_api_key="t",
        canvas_base_url="https://example.com/",
    )
    assert not cfg.canvas_base_url.endswith("/")


def test_validate_missing_token():
    cfg = Config(canvas_api_key="")
    with pytest.raises(ValueError, match="CANVAS_API_KEY"):
        cfg.validate_config()


def test_validate_with_token():
    cfg = Config(canvas_api_key="some-token")
    cfg.validate_config()  # should not raise

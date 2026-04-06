"""Canvas API configuration via environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Canvas LMS API configuration.

    Reads from environment variables:
      CANVAS_API_KEY  — required
      CANVAS_BASE_URL   — default https://canvas.illinois.edu
      API_TIMEOUT       — default 30 (seconds)
      CACHE_TTL         — default 300 (seconds)
    """

    canvas_api_key: str = ""
    canvas_base_url: str = "https://canvas.illinois.edu"
    api_timeout: int = 30
    cache_ttl: int = 300

    @field_validator("canvas_base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def canvas_api_url(self) -> str:
        """Full Canvas API URL (base URL + /api/v1)."""
        return f"{self.canvas_base_url}/api/v1"

    def validate_config(self) -> None:
        """Raise ValueError if required settings are missing."""
        if not self.canvas_api_key:
            raise ValueError(
                "CANVAS_API_KEY environment variable is required. "
                "Set it to your Canvas API access token."
            )

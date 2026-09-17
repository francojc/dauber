"""Smoke test: package imports and CLI entry point."""

import tomllib
from pathlib import Path

from typer.testing import CliRunner

from dauber import __version__
from dauber.cli.app import app

runner = CliRunner()


def _pyproject_version() -> str:
    """Read the package version declared in pyproject.toml."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def test_version_import():
    assert __version__ == _pyproject_version()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert _pyproject_version() in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Canvas LMS" in result.output

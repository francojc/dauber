"""Smoke test: package imports and CLI entry point."""

from typer.testing import CliRunner

from dauber import __version__
from dauber.cli.app import app

runner = CliRunner()


def test_version_import():
    assert __version__ == "0.1.7"


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.7" in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Canvas LMS" in result.output

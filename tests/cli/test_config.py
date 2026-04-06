"""Tests for dauber.cli.config."""

from unittest.mock import patch

from typer.testing import CliRunner

from dauber.cli.app import app

runner = CliRunner()


def test_config_show_no_config():
    with (
        patch("dauber.cli.config.read_global_config", return_value={}),
        patch("dauber.cli.config.read_local_config", return_value={}),
    ):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "No configuration found" in result.output


def test_config_show_global_only():
    global_cfg = {"level": "undergraduate", "feedback_language": "English"}
    with (
        patch("dauber.cli.config.read_global_config", return_value=global_cfg),
        patch("dauber.cli.config.read_local_config", return_value={}),
    ):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "undergraduate" in result.output
        assert "[global]" in result.output


def test_config_show_local_overrides_global():
    global_cfg = {"level": "graduate"}
    local_cfg = {"level": "undergraduate", "course_title": "Test Course"}
    with (
        patch("dauber.cli.config.read_global_config", return_value=global_cfg),
        patch("dauber.cli.config.read_local_config", return_value=local_cfg),
    ):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "undergraduate" in result.output
        assert "[local]" in result.output
        assert "Test Course" in result.output


def test_config_show_not_set_fields():
    local_cfg = {"course_title": "Test"}
    with (
        patch("dauber.cli.config.read_global_config", return_value={}),
        patch("dauber.cli.config.read_local_config", return_value=local_cfg),
    ):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "[not set]" in result.output


def test_config_init_interactive(tmp_path):
    inputs = "\n".join(
        [
            "Test Course",  # course_title
            "TST-101",  # course_code
            "99999",  # canvas_course_id
            "Spring",  # term
            "2026",  # year
            "undergraduate",  # level
            "English",  # feedback_language
            "n",  # language_learning
            "NA",  # language_level
            "casual",  # formality
            "n",  # anonymize
        ]
    )
    with (
        patch("dauber.cli.config.read_global_config", return_value={}),
        patch("dauber.cli.config.read_local_config", return_value={}),
        patch(
            "dauber.cli.config.write_local_config",
            return_value=tmp_path / "dauber" / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(
            app, ["config", "init", "--base", str(tmp_path)], input=inputs
        )
        assert result.exit_code == 0
        assert "Wrote" in result.output
        mock_write.assert_called_once()
        data = mock_write.call_args[0][0]
        assert data["course_title"] == "Test Course"
        assert data["canvas_course_id"] == 99999
        assert data["language_learning"] is False


def test_config_init_prefills_from_global(tmp_path):
    global_cfg = {"level": "graduate", "feedback_language": "Spanish"}
    # Just press enter for each prompt to accept defaults
    inputs = "\n".join(
        [
            "Test Course",  # course_title (no global default)
            "TST-101",  # course_code
            "99999",  # canvas_course_id
            "Spring",  # term
            "2026",  # year
            "",  # level (should prefill "graduate")
            "",  # feedback_language (should prefill "Spanish")
            "n",  # language_learning
            "NA",  # language_level
            "casual",  # formality
            "n",  # anonymize
        ]
    )
    with (
        patch("dauber.cli.config.read_global_config", return_value=global_cfg),
        patch("dauber.cli.config.read_local_config", return_value={}),
        patch(
            "dauber.cli.config.write_local_config",
            return_value=tmp_path / "dauber" / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(
            app, ["config", "init", "--base", str(tmp_path)], input=inputs
        )
        assert result.exit_code == 0
        data = mock_write.call_args[0][0]
        assert data["level"] == "graduate"
        assert data["feedback_language"] == "Spanish"


def test_config_global_interactive(tmp_path):
    inputs = "\n".join(
        [
            "Test User",  # name
            "Test University",  # institution
            "undergraduate",  # level
            "English",  # feedback_language
            "casual",  # formality
            "n",  # language_learning
        ]
    )
    with (
        patch("dauber.cli.config.read_global_config", return_value={}),
        patch(
            "dauber.cli.config.write_global_config",
            return_value=tmp_path / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(app, ["config", "global"], input=inputs)
        assert result.exit_code == 0
        assert "Wrote" in result.output
        mock_write.assert_called_once()
        data = mock_write.call_args[0][0]
        assert data["name"] == "Test User"
        assert data["institution"] == "Test University"


def test_config_global_prefills_existing(tmp_path):
    existing = {"name": "Old Name", "institution": "Old U"}
    inputs = "\n".join(
        [
            "",  # name (accept Old Name)
            "",  # institution (accept Old U)
            "graduate",  # level
            "Spanish",  # feedback_language
            "formal",  # formality
            "y",  # language_learning
        ]
    )
    with (
        patch("dauber.cli.config.read_global_config", return_value=existing),
        patch(
            "dauber.cli.config.write_global_config",
            return_value=tmp_path / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(app, ["config", "global"], input=inputs)
        assert result.exit_code == 0
        data = mock_write.call_args[0][0]
        assert data["name"] == "Old Name"
        assert data["institution"] == "Old U"
        assert data["language_learning"] is True


def test_config_global_defaults_flag(tmp_path):
    """--defaults writes config without prompting."""
    with (
        patch("dauber.cli.config.read_global_config", return_value={}),
        patch(
            "dauber.cli.config.write_global_config",
            return_value=tmp_path / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(app, ["config", "global", "--defaults"])
        assert result.exit_code == 0
        assert "Wrote" in result.output
        mock_write.assert_called_once()
        data = mock_write.call_args[0][0]
        assert data["level"] == "undergraduate"
        assert data["feedback_language"] == "English"
        assert data["language_learning"] is False


def test_config_global_defaults_preserves_existing(tmp_path):
    """--defaults merges existing values over defaults."""
    existing = {"name": "Jane Doe", "institution": "State U"}
    with (
        patch("dauber.cli.config.read_global_config", return_value=existing),
        patch(
            "dauber.cli.config.write_global_config",
            return_value=tmp_path / "config.toml",
        ) as mock_write,
    ):
        result = runner.invoke(app, ["config", "global", "--defaults"])
        assert result.exit_code == 0
        data = mock_write.call_args[0][0]
        assert data["name"] == "Jane Doe"
        assert data["institution"] == "State U"
        assert data["level"] == "undergraduate"

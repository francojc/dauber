"""Tests for dauber.cli.commands."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from dauber.cli.app import app

runner = CliRunner()


def _setup_source(tmp_path: Path) -> Path:
    """Create a fake repo root with one command group."""
    repo = tmp_path / "repo"
    src = repo / ".claude" / "commands" / "assess"
    src.mkdir(parents=True)
    (src / "setup.md").write_text("# setup")
    (src / "ai-pass.md").write_text("# ai-pass")
    return repo


def test_commands_install_global(tmp_path):
    """Default install copies to ~/.claude/commands/."""
    repo = _setup_source(tmp_path)
    home = tmp_path / "home"

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._COMMAND_GROUPS", ["assess"]),
        patch("pathlib.Path.home", return_value=home),
    ):
        result = runner.invoke(app, ["commands", "install"])

    assert result.exit_code == 0
    assert "Installed assess/ai-pass.md" in result.output
    assert "Installed assess/setup.md" in result.output
    assert (home / ".claude" / "commands" / "assess" / "setup.md").is_file()


def test_commands_install_local(tmp_path):
    """--local installs to ./.claude/commands/ in cwd."""
    repo = _setup_source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._COMMAND_GROUPS", ["assess"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--local"])

    assert result.exit_code == 0
    assert "Installed assess/setup.md" in result.output
    dst = project / ".claude" / "commands" / "assess" / "setup.md"
    assert dst.is_file()
    assert dst.read_text() == "# setup"


def test_commands_install_skip_existing(tmp_path):
    """Existing files are skipped without --overwrite."""
    repo = _setup_source(tmp_path)
    home = tmp_path / "home"
    existing = home / ".claude" / "commands" / "assess"
    existing.mkdir(parents=True)
    (existing / "setup.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._COMMAND_GROUPS", ["assess"]),
        patch("pathlib.Path.home", return_value=home),
    ):
        result = runner.invoke(app, ["commands", "install"])

    assert result.exit_code == 0
    assert "Skipping assess/setup.md" in result.output
    assert (existing / "setup.md").read_text() == "# old"


def test_commands_install_overwrite(tmp_path):
    """--overwrite replaces existing files."""
    repo = _setup_source(tmp_path)
    home = tmp_path / "home"
    existing = home / ".claude" / "commands" / "assess"
    existing.mkdir(parents=True)
    (existing / "setup.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._COMMAND_GROUPS", ["assess"]),
        patch("pathlib.Path.home", return_value=home),
    ):
        result = runner.invoke(app, ["commands", "install", "--overwrite"])

    assert result.exit_code == 0
    assert "Installed assess/setup.md" in result.output
    assert (existing / "setup.md").read_text() == "# setup"


# ---------------------------------------------------------------------------
# Pi Agent Skills tests
# ---------------------------------------------------------------------------


def _setup_pi_source(tmp_path: Path) -> Path:
    """Create a fake repo root with one Pi skill directory."""
    repo = tmp_path / "repo"
    skill = repo / ".pi" / "skills" / "assess-setup"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: assess-setup\n---\n# setup")
    return repo


def test_commands_install_pi_local(tmp_path):
    """--pi installs to ./.pi/skills/ in cwd."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi"])

    assert result.exit_code == 0
    assert "Installed assess-setup/SKILL.md" in result.output
    dst = project / ".pi" / "skills" / "assess-setup" / "SKILL.md"
    assert dst.is_file()
    assert "assess-setup" in dst.read_text()


def test_commands_install_pi_global(tmp_path):
    """--pi --global installs to ~/.pi/agent/skills/."""
    repo = _setup_pi_source(tmp_path)
    home = tmp_path / "home"

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.home", return_value=home),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi", "--global"])

    assert result.exit_code == 0
    assert "Installed assess-setup/SKILL.md" in result.output
    dst = home / ".pi" / "agent" / "skills" / "assess-setup" / "SKILL.md"
    assert dst.is_file()


def test_commands_install_pi_skip_existing(tmp_path):
    """Pi skills: existing SKILL.md is skipped without --overwrite."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    existing = project / ".pi" / "skills" / "assess-setup"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi"])

    assert result.exit_code == 0
    assert "Skipping assess-setup" in result.output
    assert (existing / "SKILL.md").read_text() == "# old"


def test_commands_install_pi_overwrite(tmp_path):
    """Pi skills: --overwrite replaces existing SKILL.md."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    existing = project / ".pi" / "skills" / "assess-setup"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi", "--overwrite"])

    assert result.exit_code == 0
    assert "Installed assess-setup/SKILL.md" in result.output
    assert (existing / "SKILL.md").read_text() != "# old"


def test_commands_install_pi_local_mutual_exclusion(tmp_path):
    """--pi and --local are mutually exclusive."""
    result = runner.invoke(app, ["commands", "install", "--pi", "--local"])
    assert result.exit_code == 1
    assert "--local is for Claude Code" in result.output


def test_commands_install_global_without_pi(tmp_path):
    """--global without --pi is an error."""
    result = runner.invoke(app, ["commands", "install", "--global"])
    assert result.exit_code == 1
    assert "--global is only valid with --pi" in result.output

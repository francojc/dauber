"""Tests for dauber.core.config_files."""

from dauber.core.config_files import (
    merge_configs,
    read_global_config,
    read_local_config,
    write_global_config,
    write_local_config,
)


def test_read_global_config_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "dauber.core.config_files.GLOBAL_CONFIG_PATH", tmp_path / "nope.toml"
    )
    assert read_global_config() == {}


def test_write_and_read_global_config(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr("dauber.core.config_files.GLOBAL_CONFIG_PATH", cfg_path)
    monkeypatch.setattr("dauber.core.config_files.GLOBAL_CONFIG_DIR", tmp_path)

    data = {"name": "Test User", "institution": "Test U", "level": "undergraduate"}
    result = write_global_config(data)
    assert result == cfg_path
    assert cfg_path.is_file()

    loaded = read_global_config()
    assert loaded["name"] == "Test User"
    assert loaded["institution"] == "Test U"


def test_read_local_config_missing(tmp_path):
    assert read_local_config(tmp_path) == {}


def test_write_and_read_local_config(tmp_path):
    data = {
        "course_title": "Test Course",
        "course_code": "TST-101",
        "canvas_course_id": 12345,
        "term": "Spring",
        "year": 2026,
        "level": "undergraduate",
        "feedback_language": "English",
        "language_learning": False,
        "language_level": "NA",
        "formality": "casual",
    }
    path = write_local_config(data, tmp_path)
    assert path == tmp_path / "dauber" / "config.toml"
    assert path.is_file()

    loaded = read_local_config(tmp_path)
    assert loaded["course_title"] == "Test Course"
    assert loaded["canvas_course_id"] == 12345
    assert loaded["language_learning"] is False


def test_merge_configs_local_wins():
    global_cfg = {"level": "graduate", "feedback_language": "Spanish"}
    local_cfg = {"level": "undergraduate", "course_title": "My Course"}
    merged = merge_configs(global_cfg, local_cfg)

    by_key = {k: (v, s) for k, v, s in merged}
    assert by_key["level"] == ("undergraduate", "local")
    assert by_key["course_title"] == ("My Course", "local")


def test_merge_configs_falls_back_to_global():
    global_cfg = {"feedback_language": "Spanish"}
    local_cfg = {"course_title": "My Course"}
    merged = merge_configs(global_cfg, local_cfg)

    by_key = {k: (v, s) for k, v, s in merged}
    assert by_key["feedback_language"] == ("Spanish", "global")


def test_merge_configs_not_set():
    merged = merge_configs({}, {})
    by_key = {k: (v, s) for k, v, s in merged}
    assert by_key["course_title"] == (None, "not set")
    assert by_key["canvas_course_id"] == (None, "not set")


def test_write_local_creates_directories(tmp_path):
    data = {"course_title": "Test"}
    path = write_local_config(data, tmp_path)
    assert path.parent.is_dir()
    assert path.is_file()


def test_write_global_creates_directories(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "dir"
    monkeypatch.setattr("dauber.core.config_files.GLOBAL_CONFIG_DIR", nested)
    monkeypatch.setattr(
        "dauber.core.config_files.GLOBAL_CONFIG_PATH", nested / "config.toml"
    )
    write_global_config({"name": "Test"})
    assert (nested / "config.toml").is_file()


def test_xdg_config_home_respected(tmp_path, monkeypatch):
    """XDG_CONFIG_HOME is respected when the module constants are recomputed."""
    xdg_dir = tmp_path / "custom-xdg"
    monkeypatch.setattr("dauber.core.config_files.GLOBAL_CONFIG_DIR", xdg_dir / "dauber")
    monkeypatch.setattr(
        "dauber.core.config_files.GLOBAL_CONFIG_PATH",
        xdg_dir / "dauber" / "config.toml",
    )
    write_global_config({"name": "XDG User"})
    loaded = read_global_config()
    assert loaded["name"] == "XDG User"

"""Tests for dauber.cli._output — CSV format and format_output()."""

import io
import sys

from dauber.cli._output import OutputFormat, format_output


def _capture_csv(data, headers=None):
    """Call format_output with CSV format and capture stdout."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        format_output(data, OutputFormat.CSV, headers=headers)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


# -- CSV: list of dicts --


def test_csv_list():
    data = [
        {"id": 1, "name": "Alice", "score": 95},
        {"id": 2, "name": "Bob", "score": 88},
    ]
    out = _capture_csv(data)
    lines = out.strip().splitlines()
    assert lines[0] == "id,name,score"
    assert lines[1] == "1,Alice,95"
    assert lines[2] == "2,Bob,88"


def test_csv_list_with_headers():
    data = [
        {"id": 1, "name": "Alice", "score": 95, "extra": "x"},
        {"id": 2, "name": "Bob", "score": 88, "extra": "y"},
    ]
    out = _capture_csv(data, headers=["id", "name"])
    lines = out.strip().splitlines()
    assert lines[0] == "id,name"
    assert lines[1] == "1,Alice"
    assert lines[2] == "2,Bob"


# -- CSV: single dict --


def test_csv_single_dict():
    data = {"id": 1, "name": "Alice", "score": 95}
    out = _capture_csv(data)
    lines = out.strip().splitlines()
    assert lines[0] == "id,name,score"
    assert lines[1] == "1,Alice,95"
    assert len(lines) == 2


# -- CSV: empty data --


def test_csv_empty_list():
    out = _capture_csv([])
    assert out == ""


# -- CSV: values with commas and quotes --


def test_csv_quoting():
    data = [{"name": 'O"Brien', "desc": "a, b, c"}]
    out = _capture_csv(data)
    lines = out.strip().splitlines()
    assert lines[0] == "name,desc"
    # csv module wraps fields containing commas/quotes
    assert '"a, b, c"' in lines[1]


# -- CSV: missing keys --


def test_csv_missing_keys():
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2},
    ]
    out = _capture_csv(data, headers=["id", "name"])
    lines = out.strip().splitlines()
    assert lines[2] == "2,"

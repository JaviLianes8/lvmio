"""Command line contracts from the third blind mutation review."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from _clirun import env, run, run_bytes

from lvmio import format_lvm

HEAD = "LabVIEW Measurement\t\nX_Columns\tOne\n***End_of_Header***\t\n\n"


def _file(tmp_path: Path, text: str) -> str:
    path = tmp_path / "f.lvm"
    path.write_text(text, encoding="utf-8", newline="")
    return os.fspath(path)


def test_stdin_honours_the_encoding_option(cli: list[str]) -> None:
    data = format_lvm({"V": [1.0]}, operator="lab").encode("utf-16")
    result = run_bytes(cli, "header", "-", "--encoding", "utf-16", stdin=data)
    assert result.returncode == 0
    assert b"operator: lab" in result.stdout


def test_an_unencodable_name_is_backslash_escaped_not_an_error(
    cli: list[str], tmp_path: Path
) -> None:
    path = tmp_path / "s.lvm"
    path.write_bytes(format_lvm({"N\\udc80": [1.0]}).encode("ascii"))
    child = dict(env(), PYTHONIOENCODING="cp1252")
    command = [*cli, "channels", os.fspath(path), "--encoding", "unicode_escape"]
    result = subprocess.run(command, capture_output=True, env=child, check=False)
    assert result.returncode == 0, result.stderr
    assert b"N\\udc80" in result.stdout


def test_an_unreadable_path_error_has_no_errno_prefix(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "header", os.fspath(tmp_path))
    assert result.returncode == 1
    assert result.stderr.startswith("lvmio: error: ")
    assert "[Errno" not in result.stderr


def test_a_long_missing_file_name_is_shortened(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "header", os.fspath(tmp_path / ("x" * 100 + ".lvm")))
    assert result.returncode == 1
    assert "characters)" in result.stderr
    assert "x" * 60 not in result.stderr


def test_header_json_multi_headings_is_a_boolean(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "header", _file(tmp_path, format_lvm({"V": [1.0]})), "--json")
    assert json.loads(result.stdout)["multi_headings"] is False


def test_channels_says_zero_samples_in_plural(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "channels", _file(tmp_path, format_lvm({"A": [], "B": [1.0]})))
    assert "  A: 0 samples" in result.stdout.splitlines()


def test_dump_time_of_a_segment_without_channels_prints_the_x_header(
    cli: list[str], tmp_path: Path
) -> None:
    text = HEAD + "Channels\t0\n***End_of_Header***\t\nX_Value\tComment\n0\n"
    result = run(cli, "dump", _file(tmp_path, text), "--time")
    assert result.returncode == 0
    assert result.stdout == "X_Value\n"


def test_dump_json_is_indented(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "dump", _file(tmp_path, format_lvm({"V": [1.0]})), "--format", "json")
    assert result.stdout.startswith('[\n  {\n    "name": "V"')


def test_dump_shared_time_column_follows_the_longest_channel(
    cli: list[str], tmp_path: Path
) -> None:
    path = _file(tmp_path, format_lvm({"A": [1.0, 2.0, 3.0], "B": [1.0]}))
    assert run(cli, "dump", path, "--time").stdout.splitlines()[2] == "1.0,2.0,"

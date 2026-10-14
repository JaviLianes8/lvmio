"""The command line promises beyond the happy path, as real processes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _clirun import env, run, run_bytes

import lvmio

LABVIEW = Path(__file__).parent / "fixtures" / "labview2026"


def test_python_dash_m_runs_the_same_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lvmio", "--version"], capture_output=True, text=True, env=env()
    )
    assert (result.returncode, result.stdout.strip()) == (0, f"lvmio {lvmio.__version__}")


def test_a_windows_1252_file_is_read_without_an_encoding(cli: list[str]) -> None:
    result = run_bytes(cli, "channels", str(LABVIEW / "read" / "lvmio_cp1252.lvm"))
    assert result.returncode == 0
    assert "Temperatura \u00b5 [\u00b0C]" in result.stdout.decode("utf-8", "replace") or (
        b"Temperatura" in result.stdout
    )


def test_encoding_option_is_applied_and_checked(cli: list[str]) -> None:
    path = str(LABVIEW / "comment_cp1252.lvm")
    assert run(cli, "header", path, "--encoding", "cp1252").returncode == 0
    wrong = run(cli, "header", path, "--encoding", "utf-8")
    assert wrong.returncode == 1
    assert wrong.stderr.strip() == "lvmio: error: not utf-8 text at byte 556"
    unknown = run(cli, "header", path, "--encoding", "no-such-codec")
    assert unknown.returncode == 1
    assert unknown.stderr.strip() == "lvmio: error: unknown encoding: no-such-codec"


def test_standard_input_is_read_as_bytes(cli: list[str]) -> None:
    data = (LABVIEW / "comment_cp1252.lvm").read_bytes()
    result = run_bytes(cli, "header", "-", stdin=data)
    assert result.returncode == 0
    assert b"decimal_separator: ," in result.stdout


def test_json_dump_stays_valid_json_with_infinities(cli: list[str]) -> None:
    result = run(cli, "dump", str(LABVIEW / "specials.lvm"), "--format", "json", "--time")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload[0]["data"] == [1.0, None, -0.0]
    assert payload[1]["data"] == ["Inf", "-Inf", 0.0]
    assert payload[0]["time"] == [0.0, 1.0, 2.0]


def test_multi_x_columns_dump(cli: list[str]) -> None:
    result = run(cli, "dump", str(LABVIEW / "x_columns_multi.lvm"))
    assert result.stdout.splitlines() == [
        "Untitled,Untitled 1",
        "1.0,4.0",
        "2.5,5.0",
        "-3.25,6.0",
    ]


def test_a_huge_bad_cell_is_not_echoed_back(cli: list[str], tmp_path: Path) -> None:
    raw = (LABVIEW / "x_columns_one.lvm").read_bytes().replace(b"2,500000", b"9" * 200_000 + b"x")
    path = tmp_path / "bad.lvm"
    path.write_bytes(raw)
    result = run(cli, "channels", str(path))
    assert result.returncode == 1
    assert len(result.stderr) < 200
    assert "line 24: not a number" in result.stderr


def test_segment_out_of_range_and_a_directory(cli: list[str], tmp_path: Path) -> None:
    out = run(cli, "dump", str(LABVIEW / "x_columns_one.lvm"), "--segment", "5")
    assert out.returncode == 1
    assert out.stderr.strip() == "lvmio: error: segment 5 out of range (file has 1)"
    folder = run(cli, "header", str(tmp_path))
    assert folder.returncode == 1
    assert folder.stderr.startswith("lvmio: error: ")
    assert "Traceback" not in folder.stderr


def test_a_closed_output_pipe_exits_quietly(cli: list[str]) -> None:
    with subprocess.Popen(
        [*cli, "dump", str(LABVIEW / "numbers.lvm")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env(),
    ) as proc:
        assert proc.stdout is not None and proc.stderr is not None
        proc.stdout.read(10)
        proc.stdout.close()
        err = proc.stderr.read()
        code = proc.wait()
    assert b"Traceback" not in err
    assert code in (0, 1, 120) or code < 0

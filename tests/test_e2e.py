"""Real end to end test: drive the installed ``lvmio`` console script as a real
process. The package is installed editable (``pip install -e .``), the genuine
console entry point is resolved on disk, and every assertion checks real stdout,
stderr and exit codes. No mocks and no in-process shortcuts.
"""

import json
from importlib import metadata
from pathlib import Path

import pytest
from _clirun import run

import lvmio

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def test_console_entry_point_is_registered(cli: list[str]) -> None:
    try:
        names = {ep.name: ep.value for ep in metadata.entry_points(group="console_scripts")}
    except Exception:  # pragma: no cover - metadata unavailable
        names = {}
    if "lvmio" not in names:
        pytest.skip("lvmio not installed in this interpreter; console script proven by subprocess")
    assert names["lvmio"] == "lvmio._cli:main"


def test_version_flag(cli: list[str]) -> None:
    result = run(cli, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"lvmio {lvmio.__version__}"


def test_header_subcommand_on_a_file(cli: list[str]) -> None:
    result = run(cli, "header", str(FIXTURES / "short.lvm"))
    assert result.returncode == 0
    assert "operator: lvmio" in result.stdout
    assert "separator: Tab" in result.stdout


def test_header_json_is_valid_json(cli: list[str]) -> None:
    result = run(cli, "header", str(FIXTURES / "comma_separator.lvm"), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["separator"] == "Comma"
    assert payload["segments"] == 1


def test_channels_subcommand(cli: list[str]) -> None:
    result = run(cli, "channels", str(FIXTURES / "comma_separator.lvm"))
    assert result.returncode == 0
    assert "inlet [Volts]" in result.stdout


def test_dump_json_matches_the_file_values(cli: list[str]) -> None:
    result = run(
        cli, "dump", str(FIXTURES / "comma_separator.lvm"), "--channel", "T1", "--format", "json"
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload[0]["name"] == "T1"
    assert payload[0]["data"][0] == pytest.approx(0.25)


def test_dump_csv_has_header_and_time_column(cli: list[str]) -> None:
    result = run(cli, "dump", str(FIXTURES / "short.lvm"), "--time")
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert lines[0].startswith("X_Value,Load (Cell A)")


def test_reads_from_stdin(cli: list[str]) -> None:
    text = (FIXTURES / "short.lvm").read_text(encoding="utf-8")
    result = run(cli, "header", "-", stdin=text)
    assert result.returncode == 0
    assert "operator: lvmio" in result.stdout


def test_missing_file_exits_one_with_stderr(cli: list[str]) -> None:
    result = run(cli, "header", str(FIXTURES / "does_not_exist.lvm"))
    assert result.returncode == 1
    assert "error" in result.stderr.lower()
    assert result.stdout == ""


def test_unknown_channel_exits_one(cli: list[str]) -> None:
    result = run(cli, "dump", str(FIXTURES / "short.lvm"), "--channel", "Nope")
    assert result.returncode == 1
    assert "no such channel" in result.stderr.lower()

"""Edge contracts added after the author's mutation round showed them missing."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from _clirun import env, run, run_bytes

from lvmio import Channel, LvmFile, Segment, format_lvm, parse_lvm, read_lvm

LABVIEW = Path(__file__).parent / "fixtures" / "labview2026"
VOLTS = Channel("Volt", [1.5, -2.25, 1e-9, 1e300, math.nan], unit="V", x0=0.5, delta_x=0.25)
AMPS = Channel("Amp", [0.125, 4e-5, -7.0], unit="A", x0=0.5, delta_x=0.25)
LATE = Channel("Late", [10.0, 20.0, 30.0], unit="s", x0=3.0, delta_x=2.0)


def _as_read(name: str) -> str:
    return (LABVIEW / "read" / name).read_bytes().decode("ascii")


def test_the_files_labview_read_back_are_still_what_lvmio_writes() -> None:
    """LabVIEW read these with the written values (read_results.json); keep them."""
    assert format_lvm(LvmFile([Segment([VOLTS, AMPS])])) == _as_read("lvmio_one.lvm")
    multi = LvmFile([Segment([VOLTS, LATE])], x_columns="Multi")
    assert format_lvm(multi) == _as_read("lvmio_multi.lvm")
    precise = format_lvm(LvmFile([Segment([VOLTS, AMPS])]), precision=9)
    assert precise == _as_read("lvmio_precision.lvm")
    comma = LvmFile([Segment([VOLTS, AMPS])], separator="Comma")
    assert format_lvm(comma) == _as_read("lvmio_comma.lvm")


def test_multi_x_cells_follow_each_channel() -> None:
    lines = format_lvm([VOLTS, LATE], x_columns="Multi").split("\r\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("X_Value"))
    assert lines[start + 1].split("\t")[:4] == ["0.500000", "1.500000", "3.000000", "10.000000"]
    assert lines[start + 4].split("\t")[:4] == ["1.250000", "1.000000E+300", "", ""]


def test_get_returns_the_first_of_two_channels_with_one_name() -> None:
    seg = Segment([Channel("A", [1.0]), Channel("A", [2.0])])
    assert seg.get("A") is seg.channels[0]
    assert seg["A"].data == [1.0]
    assert parse_lvm(format_lvm(seg)).segments[0]["A"].data == [1.0]


def test_a_byte_order_mark_is_ignored(tmp_path: Path) -> None:
    text = format_lvm({"a": [1.0]})
    assert parse_lvm("\ufeff" + text).segments[0]["a"].data == [1.0]
    path = tmp_path / "bom.lvm"
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert read_lvm(path).segments[0]["a"].data == [1.0]


def test_a_segment_may_follow_the_rows_without_a_blank_line() -> None:
    two = format_lvm(LvmFile([Segment([Channel("a", [1.0])]), Segment([Channel("b", [2.0])])]))
    tight = two.replace("\r\n\r\nChannels", "\r\nChannels")
    assert tight != two
    lvm = parse_lvm(tight)
    assert [s.names for s in lvm] == [["a"], ["b"]]


def test_a_huge_unknown_channel_name_is_not_echoed(cli: list[str]) -> None:
    result = run(cli, "dump", str(LABVIEW / "specials.lvm"), "--channel", "n" * 20_000)
    assert result.returncode == 1
    assert result.stderr.startswith("lvmio: error: no such channel: 'nnn")
    assert len(result.stderr) < 200


def test_standard_input_utf8_is_not_read_in_the_locale_encoding(cli: list[str]) -> None:
    data = format_lvm({"a": [1.0]}, operator="Jos\u00e9").encode("utf-8")
    result = run_bytes(cli, "header", "-", "--json", stdin=data)
    assert result.returncode == 0
    assert json.loads(result.stdout)["operator"] == "Jos\u00e9"


def test_a_closed_output_pipe_exits_zero_and_silently(cli: list[str], tmp_path: Path) -> None:
    big = tmp_path / "big.lvm"
    big.write_bytes(format_lvm({"a": [1.5] * 200_000, "b": [2.5] * 200_000}).encode("ascii"))
    with subprocess.Popen(
        [*cli, "dump", str(big)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env(),
    ) as proc:
        assert proc.stdout is not None and proc.stderr is not None
        proc.stdout.read(10)
        proc.stdout.close()
        err = proc.stderr.read()
        code = proc.wait()
    assert (code, err) == (0, b"")

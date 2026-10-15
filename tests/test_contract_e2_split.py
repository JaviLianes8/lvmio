"""Splitting, writer and command line contracts from the second blind mutation review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_contract_e2_read import HEAD, parse, seg, xrows

import lvmio
from lvmio._cli import main


def test_a_later_write_close_to_the_header_step_keeps_it() -> None:
    rows = ["0.000000\t1.0", "1.000\t1.0\tw2", "1.333\t1.0", "1.666\t1.0"]
    body = seg(rows, dx="Delta_X\t0.333333\t")
    assert parse(HEAD, body).segments[1]["V"].delta_x == 0.333333


def test_a_later_write_within_the_header_digit_keeps_the_header_step() -> None:
    rows = ["0.000000\t1.0", "0.000000\t1.0\tw2", "0.120000\t1.0", "0.240000\t1.0"]
    body = seg(rows, dx="Delta_X\t0.1\t")
    assert parse(HEAD, body).segments[1]["V"].delta_x == 0.1


def test_a_jump_splits_without_a_delta_x_line() -> None:
    body = seg(xrows("0.000000", "1.000000", "2.000000", "3.300000"), dx=None)
    assert len(parse(HEAD, body)) == 2


def test_a_later_write_step_is_rounded_to_its_digits() -> None:
    body = seg(["0.000000\t1.0", "0.100000\t1.0\tw2", "0.300000\t1.0", "0.500000\t1.0"])
    assert parse(HEAD, body).segments[1]["V"].delta_x == 0.2


def test_a_later_write_step_from_cells_of_mixed_digits() -> None:
    body = seg(["0.000000\t1.0", "0.1\t1.0\tw2", "0.35\t1.0", "0.6\t1.0"])
    assert parse(HEAD, body).segments[1]["V"].delta_x == 0.2


def test_a_step_on_the_allowance_boundary_does_not_split() -> None:
    assert len(parse(HEAD, seg(xrows("1", "3.0000000000000018"), dx=None))) == 1


def test_an_infinite_x_cell_is_passed_over() -> None:
    body = seg(xrows("0.000000", "1.000000", "Inf", "3.000000"))
    assert len(parse(HEAD, body)) == 2


@pytest.mark.parametrize("power", ["+100", "-5"])
def test_a_jump_in_exponent_notation_splits(power: str) -> None:
    cells = [f"{d}.000000E{power}" for d in (1, 2, 5)]
    body = seg(xrows(*cells), dx=f"Delta_X\t1.000000E{power}\t")
    assert len(parse(HEAD, body)) == 2


def test_each_write_measures_rounding_from_its_own_origin() -> None:
    body = seg(
        xrows("1.000000E+10", "0.000000", "0.001000", "0.002005"), dx="Delta_X\t1.000000E-3\t"
    )
    assert len(parse(HEAD, body)) == 3


def test_a_segment_time_is_written() -> None:
    s = lvmio.Segment([lvmio.Channel("V", [1.0])], time="10:00:00")
    assert lvmio.parse_lvm(lvmio.format_lvm(s)).segments[0].time == "10:00:00"


def test_empty_text_is_refused_as_samples() -> None:
    with pytest.raises(TypeError, match="ordered iterable"):
        lvmio.format_lvm({"V": ""})  # type: ignore[dict-item]


def test_a_mapping_key_that_is_not_str_is_named() -> None:
    with pytest.raises(TypeError, match="channel names must be str, not int"):
        lvmio.format_lvm({1: [1.0]})  # type: ignore[dict-item]


def test_notes_holding_the_separator_are_refused() -> None:
    with pytest.raises(ValueError, match="notes"):
        lvmio.format_lvm(lvmio.Segment([lvmio.Channel("V", [1.0])], notes="a\tb"))


def test_a_channel_date_holding_the_separator_is_refused() -> None:
    with pytest.raises(ValueError, match="channel date"):
        lvmio.format_lvm([lvmio.Channel("V", [1.0], date="a\tb")])


def _file(tmp_path: Path, data: object) -> str:
    path = tmp_path / "a.lvm"
    lvmio.write_lvm(path, data)  # type: ignore[arg-type]
    return str(path)


def test_header_json_is_indented_and_counts_segments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["header", _file(tmp_path, lvmio.LvmFile([])), "--json"]) == 0
    out = capsys.readouterr().out
    fields = json.loads(out)
    assert fields["segments"] == 0 and out == json.dumps(fields, indent=2) + "\n"


def test_channels_reports_the_longest_channel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["channels", _file(tmp_path, {"A": [1.0, 2.0, 3.0], "B": [1.0]})])
    assert capsys.readouterr().out.splitlines()[0] == "segment 0: 2 channels, 3 samples"


def test_dump_time_gives_channels_with_their_own_step_their_own_column(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    channels = [lvmio.Channel("A", [1.0, 2.0]), lvmio.Channel("B", [1.0, 2.0], delta_x=0.5)]
    data = lvmio.LvmFile([lvmio.Segment(channels)], x_columns="Multi")
    main(["dump", _file(tmp_path, data), "--time"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == ["X_Value,A,X_Value,B", "0.0,1.0,0.0,1.0"]


def test_dump_json_has_name_unit_and_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["dump", _file(tmp_path, [lvmio.Channel("V", [1.0], unit="V")]), "--format", "json"])
    assert json.loads(capsys.readouterr().out) == [{"name": "V", "unit": "V", "data": [1.0]}]

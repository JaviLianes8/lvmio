"""Contracts from the fourth blind mutation review: each pins one behaviour."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

import lvmio
from lvmio._cli import main

HEAD = "LabVIEW Measurement\t\nX_Columns\tOne\n***End_of_Header***\t\n\t\n"
ONE = "Channels\t1\t\nDelta_X\t1\t\n***End_of_Header***\t\t\nX_Value\tV\tComment\n"


def test_a_short_line_of_control_characters_is_quoted_cut_short() -> None:
    with pytest.raises(lvmio.LvmError) as info:
        lvmio.parse_lvm("\x01" * 40)
    assert "(40 characters)" in str(info.value)


def test_channel_lookup_is_case_sensitive() -> None:
    seg = lvmio.Segment([lvmio.Channel("V", [1.0])])
    assert seg.get("v") is None
    assert "v" not in seg


def test_version_matches_the_project_metadata() -> None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert lvmio.__version__ == match.group(1)


def test_column_names_are_read_without_surrounding_blanks() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nX_Value\t V \tComment\n0\t1.5\n"
    assert lvmio.parse_lvm(text).segments[0].names == ["V"]


def test_several_empty_cells_after_the_comment_column_are_ignored() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nX_Value\tV\tComment\t\t\n0\t1.5\tnote\n"
    seg = lvmio.parse_lvm(text).segments[0]
    assert (seg.names, seg.comment) == (["V"], "note")


def test_a_two_row_write_takes_its_step_from_its_own_rows_only() -> None:
    seg = (
        "Channels\t2\t\nDelta_X\t0.500000\t2.000000\t\n***End_of_Header***\t\t\t\n"
        "X_Value\tA\tB\tComment\n"
    )
    rows = [0, 0.5, 1, 10, 10.5, 100, 100.5, 101]
    lvm = lvmio.parse_lvm(HEAD + seg + "".join(f"{x:.6f}\t1\t2\n" for x in rows))
    assert [s.samples for s in lvm.segments] == [[3, 3], [2, 2], [3, 3]]
    assert lvm.segments[1]["B"].delta_x == 0.5


def test_the_header_step_tolerates_its_own_printed_digits() -> None:
    lvm = lvmio.parse_lvm(HEAD + ONE + "0.000000\t1\n1.400000\t2\n2.800000\t3\n")
    assert [s.samples for s in lvm.segments] == [[3]]


def test_a_write_starting_with_empty_x_keeps_the_header_step_digits() -> None:
    lvm = lvmio.parse_lvm(HEAD + ONE + "0.000000\t1\n1.400000\t2\n\t3\tb\n2.800000\t4\n")
    assert [s.samples for s in lvm.segments] == [[2], [2]]


def test_an_empty_operator_keyword_overrides_the_file_operator() -> None:
    lvm = lvmio.LvmFile([lvmio.Segment([lvmio.Channel("V", [1.0])])], operator="lab")
    assert lvmio.parse_lvm(lvmio.format_lvm(lvm, operator="")).operator == ""


def test_write_lvm_passes_x_columns_through(tmp_path: Path) -> None:
    path = tmp_path / "run.lvm"
    lvmio.write_lvm(path, {"V": [1.0]}, x_columns="No")
    assert lvmio.read_lvm(path).x_columns == "No"


def test_the_reader_version_is_written() -> None:
    lvm = lvmio.LvmFile([lvmio.Segment([lvmio.Channel("V", [1.0])])], reader_version="1")
    assert lvmio.parse_lvm(lvmio.format_lvm(lvm)).reader_version == "1"


def test_a_bad_segment_number_is_quoted_to_twenty_characters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as info:
        main(["dump", "run.lvm", "--segment", "a" * 30])
    assert info.value.code == 2
    assert "(30 characters)" in capsys.readouterr().err


def test_a_missing_standard_input_is_an_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    assert main(["header", "-"]) == 1
    assert "lvmio: error: no standard input" in capsys.readouterr().err


def test_channels_lists_every_channel(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "run.lvm"
    lvmio.write_lvm(path, {"V": [1.0], "I": [2.0, 3.0]})
    assert main(["channels", str(path)]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == ["  V: 1 sample", "  I: 2 samples"]

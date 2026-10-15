"""Contracts from the sixth blind mutation review: each pins one behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

import lvmio
from lvmio._cli import main

HEAD = "LabVIEW Measurement\t\n***End_of_Header***\t\n\n"


def test_an_unprintable_unknown_encoding_is_quoted(tmp_path: Path) -> None:
    with pytest.raises(LookupError) as info:
        lvmio.read_lvm(tmp_path / "missing.lvm", encoding="no\nsuch")
    assert str(info.value) == "unknown encoding: 'no\\nsuch'"


def test_any_two_digit_hex_escape_in_a_comment_is_decoded() -> None:
    text = HEAD + "Channels\t1\n***End_of_Header***\t\nX_Value\tV\tComment\n\t1.5\ta\\7Fb\\41\n"
    assert lvmio.parse_lvm(text).segments[0].comment == "a\x7fbA"


def test_a_segment_is_written_with_the_default_operator() -> None:
    text = lvmio.format_lvm(lvmio.Segment([lvmio.Channel("V", [1.0])]))
    assert "Operator\tunknown" in text.split("\r\n")


def test_an_unknown_layout_word_lists_the_spellings_lvmio_writes() -> None:
    with pytest.raises(ValueError, match=r"^separator must be one of Tab, Comma: 'semicolon'$"):
        lvmio.format_lvm({"V": [1.0]}, separator="semicolon")
    with pytest.raises(ValueError, match=r"^x_columns must be one of No, One, Multi: 'two'$"):
        lvmio.format_lvm({"V": [1.0]}, x_columns="two")


def test_an_error_line_of_about_a_hundred_characters_is_printed_whole(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.lvm"
    path.write_text(
        "LabVIEW Measurement\t\nDecimal_Separator\t" + ";" * 1000 + "\n***End_of_Header***\t\n",
        encoding="utf-8",
    )
    assert main(["header", str(path)]) == 1
    expected = "Decimal_Separator must be '.' or ',', not '" + ";" * 40 + "'... (1000 characters)"
    assert capsys.readouterr().err == f"lvmio: error: {expected}\n"


def test_only_the_exact_x_value_spelling_marks_an_x_column() -> None:
    text = HEAD + "Channels\t2\n***End_of_Header***\t\nx_value\tV\tComment\n1.5\t2.5\n"
    segment = lvmio.parse_lvm(text).segments[0]
    assert segment.names == ["x_value", "V"]
    assert segment["x_value"].data == [1.5]


def test_a_later_write_keeps_the_header_step_when_its_third_x_cell_is_empty() -> None:
    # Channel B's own Delta_X (2) differs from the shared X column's step (1). The later write
    # steps by 1 for two rows, then the X cell is empty, so nothing confirms a step of its own:
    # B keeps the 2 of its header.
    text = HEAD + (
        "Channels\t2\t\nDelta_X\t1.000000\t2.000000\t\n***End_of_Header***\t\t\t\n"
        "X_Value\tA\tB\tComment\n"
        "0.000000\t1\t1\n1.000000\t2\t2\n"
        "10.000000\t3\t3\tsecond\n11.000000\t4\t4\n\t5\t5\n"
    )
    later = lvmio.parse_lvm(text).segments[1]
    assert later.comment == "second"
    assert [c.x0 for c in later] == [10.0, 10.0]
    assert [c.delta_x for c in later] == [1.0, 2.0]

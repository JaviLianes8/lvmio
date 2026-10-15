"""Library contracts from the third blind mutation review: each pins one behaviour."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

import lvmio
from lvmio import Channel, Segment, format_lvm, parse_lvm

HEAD = "LabVIEW Measurement\t\nX_Columns\tOne\n***End_of_Header***\t\n\n"
SEG1 = "Channels\t1\n***End_of_Header***\t\nX_Value\tV\tComment\n"


def _one_header(rows: str) -> lvmio.LvmFile:
    return parse_lvm(HEAD + SEG1 + rows)


def test_an_empty_segment_has_length_zero() -> None:
    assert len(Segment([])) == 0


def test_read_lvm_refuses_a_bytes_encoding_with_type_error(tmp_path: Path) -> None:
    path = tmp_path / "a.lvm"
    lvmio.write_lvm(path, {"V": [1.0]})
    with pytest.raises(TypeError, match="encoding must be str, not bytes"):
        lvmio.read_lvm(path, encoding=b"utf-8")  # type: ignore[arg-type]


def test_a_header_without_separator_line_reads_as_tab() -> None:
    assert _one_header("0\t1.5\n").separator == "Tab"


def test_an_empty_x_columns_field_reads_as_one() -> None:
    text = "LabVIEW Measurement\t\nX_Columns\t\n***End_of_Header***\t\n\n" + SEG1 + "0\t1.5\n"
    assert parse_lvm(text).x_columns == "One"


def test_a_comma_only_line_in_a_comma_file_header_is_a_blank_line() -> None:
    text = (
        "LabVIEW Measurement,\nSeparator,Comma\n,,,\n***End_of_Header***,\n\n"
        "Channels,1\n***End_of_Header***,\nX_Value,V,Comment\n0,1.5\n"
    )
    with pytest.raises(lvmio.LvmError, match="before a blank line"):
        parse_lvm(text)


def test_file_header_values_are_stripped() -> None:
    text = HEAD.replace("X_Columns\tOne\n", "X_Columns\tOne\nOperator\t lab \n")
    assert parse_lvm(text + SEG1 + "0\t1.5\n").operator == "lab"


def test_a_spaces_only_line_between_segments_is_blank() -> None:
    lvm = parse_lvm(HEAD.removesuffix("\n") + "   \n" + SEG1 + "0\t1.5\n")
    assert lvm.segments[0]["V"].data == [1.5]


def test_a_segment_header_without_end_names_the_line_it_starts_on() -> None:
    with pytest.raises(lvmio.LvmError, match=r"^line 5: segment header has no"):
        parse_lvm(HEAD + "Channels\t1\nSamples\t1\n\n")


def test_padding_trim_by_samples_applies_only_to_the_first_write() -> None:
    text = (
        HEAD + "Channels\t2\t\t\nSamples\t2\t2\t\n***End_of_Header***\t\t\t\n"
        "X_Value\tA\tB\tComment\n0\t1\t1\n1\t2\t2\n0\t3\t3\tsecond\n1\t4\t\n2\t5\t\n"
    )
    second = parse_lvm(text).segments[1]
    assert second.comment == "second"
    assert len(second["B"].data) == 3


def test_a_tab_only_cell_in_a_comma_file_is_a_missing_sample() -> None:
    text = (
        "LabVIEW Measurement,\nSeparator,Comma\n***End_of_Header***,\n\n"
        "Channels,2\n***End_of_Header***,\nX_Value,A,B,Comment\n0,1,\t\n"
    )
    assert math.isnan(parse_lvm(text).segments[0]["B"].data[0])


def test_a_later_write_step_tolerance_counts_both_cells_digits() -> None:
    rows = "0.000\t1\n1.000\t1\n2.000\t1\n10.0\t1\tw2\n10.50\t1\n11.000\t1\n11.554\t1\n"
    assert len(_one_header(rows).segments) == 2


def test_an_x_step_tolerance_adds_both_cells_last_digits() -> None:
    assert len(_one_header("0\t1\n1.0\t1\n2.11\t1\n").segments) == 1


def test_an_x_cell_with_an_over_long_positive_exponent_never_starts_a_write() -> None:
    rows = "0.000\t1\n1.000\t1\n2.000\t1\n3.500E+00000\t1\n"
    assert len(_one_header(rows).segments) == 1


def test_padding_is_trimmed_for_channels_of_a_thousand_samples() -> None:
    lvm = parse_lvm(format_lvm({"A": [0.0] * 1000, "B": [0.0] * 1001}))
    assert lvm.segments[0].samples == [1000, 1001]


def test_a_blank_comment_cell_does_not_start_a_write() -> None:
    assert len(_one_header("0\t1\n1\t2\t \n2\t3\n").segments) == 1


def test_a_later_write_whose_second_x_cell_is_empty_is_read() -> None:
    assert _one_header("0\t1\n1\t2\n0\t3\tw2\n\t4\n").segments[1]["V"].data == [3.0, 4.0]


def test_a_subnormal_later_write_step_keeps_its_printed_digits() -> None:
    lvm = _one_header("0\t1\n1\t1\n2\t1\n1.0E-316\t1\tw2\n2.5E-316\t1\n4.0E-316\t1\n")
    assert abs(lvm.segments[1]["V"].delta_x - 1.5e-316) < 1e-320


def test_format_lvm_refuses_a_str_as_a_whole() -> None:
    with pytest.raises(TypeError, match="cannot write str"):
        format_lvm("V")  # type: ignore[arg-type]


def test_an_x_dimension_holding_the_separator_is_refused() -> None:
    with pytest.raises(ValueError, match="x_dimension"):
        format_lvm([Channel("V", [1.0], x_dimension="a\tb")])


def test_a_segment_date_holding_the_separator_is_refused() -> None:
    with pytest.raises(ValueError, match="segment date"):
        format_lvm(Segment([Channel("V", [1.0])], date="2026\t10"))


def test_a_float_precision_is_refused_with_the_documented_message() -> None:
    with pytest.raises(TypeError, match="precision must be an int, not float"):
        format_lvm({"V": [1.0]}, precision=6.0)  # type: ignore[arg-type]


def test_the_time_keyword_sets_the_file_header_time() -> None:
    assert parse_lvm(format_lvm({"V": [1.0]}, time="12:00:00")).time == "12:00:00"


class _Int(int):
    def __int__(self) -> int:
        return 3


def test_precision_uses_the_integer_value_not_int_conversion() -> None:
    assert "\n0.000000\t1.50\r\n" in format_lvm({"V": [1.5]}, precision=_Int(2))

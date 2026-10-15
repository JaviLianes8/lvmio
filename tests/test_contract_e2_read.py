"""Reader contracts from the second blind mutation review: header fields and layouts."""

from __future__ import annotations

from pathlib import Path

import pytest

import lvmio
from lvmio import LvmFile

HEAD = [
    "LabVIEW Measurement\t",
    "Writer_Version\t2",
    "Reader_Version\t2",
    "Separator\tTab",
    "Decimal_Separator\t.",
    "Multi_Headings\tNo",
    "X_Columns\tOne",
    "Time_Pref\tRelative",
    "Operator\tlab",
    "Date\t2026/01/01",
    "Time\t10:00:00",
    "***End_of_Header***\t",
    "",
]


def seg(
    rows: list[str],
    *,
    cols: str = "X_Value\tV\tComment",
    dx: str | None = "Delta_X\t1.000000\t",
    extra: tuple[str, ...] = (),
) -> list[str]:
    lines = ["Channels\t1\t", "X_Dimension\tTime\t", "X0\t0.0000000000000000E+0\t"]
    if dx:
        lines.append(dx)
    return [*lines, *extra, "***End_of_Header***\t\t", cols, *rows]


def parse(head: list[str], body: list[str]) -> LvmFile:
    return lvmio.parse_lvm("\n".join([*head, *body, ""]))


def xrows(*xs: str) -> list[str]:
    return [f"{x}\t1.0" for x in xs]


def test_an_empty_decimal_separator_cell_means_a_period() -> None:
    head = [h if not h.startswith("Decimal") else "Decimal_Separator\t" for h in HEAD]
    assert parse(head, seg(xrows("0", "1"))).decimal_separator == "."


def test_time_pref_defaults_to_relative() -> None:
    head = [h for h in HEAD if not h.startswith("Time_Pref")]
    assert parse(head, seg(xrows("0"))).time_pref == "Relative"


def test_a_header_field_is_its_first_cell() -> None:
    head = [h if not h.startswith("Operator") else "Operator\tlab\t" for h in HEAD]
    assert parse(head, seg(xrows("0"))).operator == "lab"


def test_a_comma_file_may_name_its_separator_with_a_tab() -> None:
    head = [h.replace("\t", ",") for h in HEAD]
    head[3] = "Separator\tComma"
    body = [r.replace("\t", ",") for r in seg(xrows("0", "1"))]
    assert parse(head, body).separator == "Comma"


def test_an_unknown_encoding_is_named_plainly(tmp_path: Path) -> None:
    name = "x" * 30
    with pytest.raises(LookupError, match=f"^unknown encoding: {name}$"):
        lvmio.read_lvm(tmp_path / "a.lvm", encoding=name)


def test_parse_lvm_names_bytes_in_its_message() -> None:
    with pytest.raises(TypeError, match="parse_lvm expects str, not bytes"):
        lvmio.parse_lvm(b"LabVIEW Measurement")  # type: ignore[arg-type]


def test_an_end_marker_followed_by_a_blank_is_an_end_marker() -> None:
    end = "***End_of_Header***\t\t"
    body = [b if b != end else "***End_of_Header*** \t\t" for b in seg(xrows("0", "1"))]
    assert parse(HEAD, body).segments[0]["V"].data == [1.0, 1.0]


def test_a_repeated_file_header_right_after_rows_is_skipped() -> None:
    lvm = parse(HEAD, seg(xrows("0", "1")) + HEAD[:-1] + [""] + seg(xrows("0")))
    assert [s.samples for s in lvm] == [[2], [1]]


def test_a_lower_case_comment_column_is_the_comment_column() -> None:
    s = parse(HEAD, seg(["0\t1.0\thi"], cols="X_Value\tV\tcomment")).segments[0]
    assert s.names == ["V"] and s.comment == "hi"


def test_a_tab_after_the_comment_column_is_ignored() -> None:
    s = parse(HEAD, seg(["0\t1.0\thi"], cols="X_Value\tV\tComment\t")).segments[0]
    assert s.names == ["V"] and s.comment == "hi"


def test_a_short_x_dimension_line_leaves_later_channels_empty() -> None:
    body = [
        "Channels\t2\t",
        "X_Dimension\tTime",
        "***End_of_Header***\t\t",
        "X_Value\tA\tB\tComment",
        "0\t1\t2",
    ]
    assert [c.x_dimension for c in parse(HEAD, body).segments[0]] == ["Time", ""]


def test_the_segment_date_is_the_first_channels() -> None:
    body = [
        "Channels\t2\t",
        "Date\t2026/01/01\t2026/02/02",
        "***End_of_Header***\t\t",
        "X_Value\tA\tB\tComment",
        "0\t1\t2",
    ]
    assert parse(HEAD, body).segments[0].date == "2026/01/01"


def test_a_comment_split_without_x_keeps_the_axis_and_the_notes_once() -> None:
    head = [h if not h.startswith("X_Columns") else "X_Columns\tNo" for h in HEAD]
    rows = ["\t1.0", "\t2.0", "\t3.0\tsecond"]
    body = seg(rows, dx="Delta_X\t0.500000\t", extra=("Notes\tnote\t",))
    a, b = parse(head, body).segments
    assert b.channels[0].x0 == 1.0 and (a.notes, b.notes) == ("note", "")


def test_notes_are_the_first_non_empty_cell() -> None:
    notes = parse(HEAD, seg(xrows("0"), extra=("Notes\t\tnote",))).segments[0].notes
    assert notes == "note"


def test_header_cells_are_stripped() -> None:
    body = seg(xrows("0"), extra=("Y_Unit_Label\t V \t",))
    assert parse(HEAD, body).segments[0]["V"].unit == "V"

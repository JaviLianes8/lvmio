"""Edge contracts from the independent mutation round: defaults, CLI details, escapes."""

from __future__ import annotations

from pathlib import Path

import pytest
from _clirun import run

from lvmio import Channel, LvmError, LvmFile, Segment, format_lvm, parse_lvm, write_lvm


def _drop(text: str, key: str) -> str:
    return "\r\n".join(ln for ln in text.split("\r\n") if not ln.startswith(key + "\t"))


def _file(tmp_path: Path, data: object, **kw: object) -> str:
    path = tmp_path / "f.lvm"
    write_lvm(path, data, **kw)  # type: ignore[arg-type]
    return str(path)


def test_lower_case_hex_escapes_in_comments_are_decoded() -> None:
    text = format_lvm(Segment([Channel("V", [1.0])], comment="a\nb")).replace("\\0A", "\\0a")
    assert parse_lvm(text).segments[0].comment == "a\nb"


def test_contains_is_false_for_a_non_str_key() -> None:
    seg = Segment([Channel(5, [1.0])])  # type: ignore[arg-type]
    assert 5 not in seg


def test_a_carriage_return_in_a_field_is_refused() -> None:
    with pytest.raises(ValueError, match="line break"):
        format_lvm({"V": [1.0]}, operator="a\rb")


def test_segments_may_be_a_tuple() -> None:
    text = format_lvm(LvmFile(segments=(Segment([Channel("V", [1.0])]),)))  # type: ignore[arg-type]
    assert parse_lvm(text).segments[0]["V"].data == [1.0]


def test_cli_without_a_command_prints_help_and_exits_zero(cli: list[str]) -> None:
    result = run(cli)
    assert result.returncode == 0
    assert "usage" in result.stdout


def test_cli_segment_past_the_end_is_one_clean_line(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "dump", _file(tmp_path, {"V": [1.0]}), "--segment", "1")
    assert result.returncode == 1
    assert result.stderr.strip() == "lvmio: error: segment 1 out of range (file has 1)"


def _two_segments() -> LvmFile:
    return LvmFile([Segment([Channel("A", [1.0])]), Segment([Channel("B", [2.0])])])


def test_cli_negative_segment_counts_from_the_end(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "dump", _file(tmp_path, _two_segments()), "--segment", "-1")
    assert result.returncode == 0
    assert result.stdout == "B\n2.0\n"


def test_cli_dump_defaults_to_the_first_segment(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "dump", _file(tmp_path, _two_segments()))
    assert result.stdout == "A\n1.0\n"


def test_cli_segment_index_with_leading_zeros_is_accepted(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "dump", _file(tmp_path, {"V": [1.0]}), "--segment", "0000000")
    assert result.returncode == 0


def test_cli_missing_file_message(cli: list[str], tmp_path: Path) -> None:
    result = run(cli, "header", str(tmp_path / "missing.lvm"))
    assert result.returncode == 1
    assert result.stderr.startswith("lvmio: error: no such file: ")


def test_message_quotes_a_line_of_exactly_forty_characters_whole() -> None:
    with pytest.raises(LvmError) as info:
        parse_lvm("x" * 40)
    assert str(info.value) == "not a LabVIEW Measurement file: line 1 is '" + "x" * 40 + "'"


def test_cli_csv_writes_a_missing_sample_as_an_empty_cell(cli: list[str], tmp_path: Path) -> None:
    seg = Segment([Channel("A", [1.0, 2.0]), Channel("B", [3.0])])
    result = run(cli, "dump", _file(tmp_path, seg))
    assert result.stdout == "A,B\n1.0,3.0\n2.0,\n"


def test_cli_csv_time_columns_follow_each_channel(cli: list[str], tmp_path: Path) -> None:
    seg = Segment([Channel("A", [1.0], x0=0.0), Channel("B", [2.0, 3.0], x0=10.0)])
    path = _file(tmp_path, seg, x_columns="Multi")
    result = run(cli, "dump", path, "--time")
    assert result.stdout == "X_Value,A,X_Value,B\n0.0,1.0,10.0,2.0\n,,11.0,3.0\n"


def test_cli_csv_shared_time_column_spans_the_longest_channel(
    cli: list[str], tmp_path: Path
) -> None:
    seg = Segment([Channel("A", [1.0], x0=5.0), Channel("B", [2.0, 3.0], x0=5.0)])
    result = run(cli, "dump", _file(tmp_path, seg), "--time")
    assert result.stdout == "X_Value,A,B\n5.0,1.0,2.0\n6.0,,3.0\n"


def test_cli_channels_escapes_control_characters(cli: list[str], tmp_path: Path) -> None:
    text = format_lvm([Channel("A", [1.0], unit="V")]).replace("\tA", "\tA" + chr(27) + "[2J")
    path = tmp_path / "esc.lvm"
    path.write_bytes(text.encode())
    result = run(cli, "channels", str(path))
    assert chr(27) not in result.stdout
    assert "A" + chr(92) + "1B[2J [V]: 1 samples" in result.stdout


def test_bare_carriage_return_line_endings_are_read() -> None:
    text = format_lvm({"V": [1.5]})
    assert parse_lvm(text.replace("\r\n", "\r")).segments[0]["V"].data == [1.5]


def test_missing_file_header_fields_take_their_defaults() -> None:
    text = format_lvm({"V": [1.5]}, operator="lab", x_columns="Multi")
    for key in ("Decimal_Separator", "Writer_Version", "X_Columns", "Operator"):
        text = _drop(text, key)
    lvm = parse_lvm(text)
    assert (lvm.decimal_separator, lvm.writer_version, lvm.x_columns, lvm.operator) == (
        ".",
        "2",
        "One",
        "unknown",
    )


def test_multi_headings_and_separator_values_are_case_insensitive() -> None:
    text = format_lvm(_two_segments(), separator="Comma")
    text = text.replace("Multi_Headings,Yes", "Multi_Headings,yes")
    text = text.replace("Separator,Comma", "Separator,comma")
    lvm = parse_lvm(text)
    assert lvm.multi_headings is True
    assert lvm.segments[1]["B"].data == [2.0]


def test_a_row_with_an_empty_first_cell_after_a_blank_line_is_refused() -> None:
    text = format_lvm({"V": [1.5]}, x_columns="No") + "\r\n\t2.5\r\n"
    with pytest.raises(LvmError, match="data row after a blank line"):
        parse_lvm(text)


def test_a_file_without_an_x_value_column_reads_every_header_cell() -> None:
    text = (
        "LabVIEW Measurement\t\nSeparator\tTab\n***End_of_Header***\t\n\n"
        "Channels\t1\nX_Dimension\tVolt\nX0\t3.0\nDelta_X\t0.5\n***End_of_Header***\t\n"
        "V\tComment\n1.0\n2.0\n"
    )
    ch = parse_lvm(text).segments[0]["V"]
    assert (ch.data, ch.x0, ch.delta_x, ch.x_dimension) == ([1.0, 2.0], 3.0, 0.5, "Volt")


def test_missing_segment_header_fields_take_their_defaults() -> None:
    text = format_lvm([Channel("V", [1.0], x0=2.0, delta_x=0.5, x_dimension="Volt")])
    text = _drop(_drop(text, "Delta_X"), "X_Dimension")
    ch = parse_lvm(text).segments[0]["V"]
    assert (ch.x0, ch.delta_x, ch.x_dimension) == (2.0, 1.0, "Time")


def test_an_empty_x0_cell_means_the_default() -> None:
    text = format_lvm([Channel("V", [1.0], x0=2.0)])
    lines = [("X0\t" if ln.startswith("X0\t") else ln) for ln in text.split("\r\n")]
    assert parse_lvm("\r\n".join(lines)).segments[0]["V"].x0 == 0.0


def test_precision_zero_is_accepted() -> None:
    # The X column keeps six decimals; the sample is rounded to none, ties toward zero.
    assert format_lvm({"V": [2.5]}, precision=0).splitlines()[-2] == "0.000000\t2"


def test_write_lvm_defaults_to_utf8(tmp_path: Path) -> None:
    path = tmp_path / "f.lvm"
    write_lvm(path, {"V": [1.0]}, operator="Jos\u00e9")
    assert "Operator\tJos\u00e9".encode() in path.read_bytes()

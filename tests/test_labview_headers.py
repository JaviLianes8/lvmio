"""Header features LabVIEW writes: one header only, descriptions, per-channel dates, units."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lvmio import Channel, LvmError, LvmFile, Segment, format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
RESULTS = json.loads((HERE / "read_results.json").read_text(encoding="utf-8"))
CRLF, TAB = "\r\n", "\t"


def _raw(name: str) -> str:
    return (HERE / name).read_bytes().decode("cp1252")


def test_one_header_mode_later_writes_become_segments_with_their_comment_and_x0() -> None:
    lvm = read_lvm(HERE / "one_header_same.lvm")
    assert lvm.multi_headings is False and len(lvm) == 2
    first, later = lvm.segments
    assert [c.data for c in first] == [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]
    assert [c.data for c in later] == [[5.0, 6.0, 7.0], [8.0, 9.0, 10.0]]
    assert (first.comment, later.comment) == ("c1", "c2")
    assert later.channels[0].x0 == 0.0 and later.channels[0].time_axis() == [0.0, 1.0, 2.0]
    assert "Samples" + TAB + "3" + TAB + "3" + TAB in _raw("one_header_same.lvm")
    assert RESULTS["one_header_same.lvm"][0]["channels"] == [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("one_header_fewer.lvm", "the row has 2 cells"),
        ("one_header_more.lvm", "after the last column"),
    ],
)
def test_one_header_mode_with_another_channel_count_is_refused(name: str, message: str) -> None:
    with pytest.raises(LvmError, match=message):
        read_lvm(HERE / name)
    assert RESULTS[name][0]["error"] == 0


def test_a_file_description_round_trips_with_labview_escapes() -> None:
    lvm = read_lvm(HERE / "description.lvm")
    text = "line one" + chr(13) + chr(10) + "line two" + TAB + "x, y" + chr(92) + "z"
    assert lvm.description == text
    assert format_lvm(lvm) == _raw("description.lvm")
    comma = LvmFile([Segment([Channel("A", [1.0])])], separator="Comma", description=text)
    assert parse_lvm(format_lvm(comma)).description == text


def test_each_channel_keeps_its_own_date_and_time() -> None:
    lvm = read_lvm(HERE / "relay" / "lvmio_dates.lvm")
    first, second = lvm.segments[0]
    # LabVIEW kept each channel's date and wrote the times to the second.
    assert (first.date, first.time) == ("2026/10/14", "10:00:00,")
    assert (second.date, second.time) == ("2026/10/15", "11:30:00,")
    assert format_lvm(lvm) == _raw("relay/lvmio_dates.lvm")
    plain = format_lvm([Channel("A", [1.0]), Channel("B", [2.0], date="d")])
    assert "Date" + TAB + TAB + "d" + TAB in plain


def test_relays_and_notes_survive_a_rewrite() -> None:
    for name in (
        "lvmio_unit_gap",
        "blank_delta_x",
        "text_delta_x",
        "lvmio_dates",
        "express_default",
    ):
        assert format_lvm(parse_lvm(_raw(f"relay/{name}.lvm"))) == _raw(f"relay/{name}.lvm")
    notes = parse_lvm(_raw("relay/lvmio_unit_gap.lvm")).segments[0].notes
    assert notes == "X values guaranteed valid only for C0"
    assert "Notes" + TAB + "n" + TAB in format_lvm(Segment([Channel("A", [1.0])], notes="n"))


def test_labview_reads_a_file_without_units_as_volts() -> None:
    assert [c.unit for c in read_lvm(HERE / "express_default.lvm").segments[0]] == ["", ""]
    line = next(x for x in _raw("relay/express_default.lvm").split(CRLF) if x.startswith("Y_Unit"))
    assert line.split(TAB)[1:3] == ["V", "V"]


def test_samples_above_the_rows_is_padded_in_every_layout() -> None:
    for name in ("samples_more_than_rows_no_x", "samples_more_than_rows_multi"):
        assert RESULTS[f"read/{name}.lvm"][0]["channels"] == [[1.0, 2.0, "NaN", 0.0, 0.0]]
        assert read_lvm(HERE / "read" / f"{name}.lvm").segments[0].channels[0].data == [1.0, 2.0]
    two = RESULTS["read/samples_more_multi_two_channels.lvm"][0]["channels"]
    assert two == [[1.0, 2.0, "NaN", 0.0, 0.0], [3.0, 4.0, "NaN", 0.0, 0.0]]
    assert RESULTS["read/no_date_time_lines.lvm"][0]["error"] == 100
    assert read_lvm(HERE / "read" / "no_date_time_lines.lvm").segments[0].names == ["A", "B"]


def test_a_later_write_that_jumps_or_changes_step_keeps_its_x_axis() -> None:
    gap = read_lvm(HERE / "one_header_gap.lvm")
    assert [(s.channels[0].x0, s.channels[0].data) for s in gap] == [
        (0.0, [1.0, 2.0, 3.0]),
        (6.0, [7.0, 8.0, 9.0]),
    ]
    step = read_lvm(HERE / "one_header_step.lvm")
    # The later write's first row continues the X of the first write, so it stays there.
    assert [c.time_axis() for s in step for c in s] == [[0.0, 1.0, 2.0, 3.0], [3.5, 4.0]]
    assert [v for s in step for v in s.channels[0].data] == [1.0, 2.0, 3.0, 7.0, 8.0, 9.0]
    for name in ("one_header_gap.lvm", "one_header_step.lvm"):
        assert RESULTS[name][0]["channels"] == [[1.0, 2.0, 3.0]]


def test_a_negative_increment_is_one_segment_and_round_trips() -> None:
    lvm = read_lvm(HERE / "negative_dx.lvm")
    assert len(lvm) == 1 and lvm.segments[0].channels[0].delta_x == -1.0
    assert format_lvm(lvm) == _raw("negative_dx.lvm")
    ours = LvmFile([Segment([Channel("V", [1.0, 2.0, 3.0], delta_x=-1e-7)])])
    assert len(parse_lvm(format_lvm(ours))) == 1

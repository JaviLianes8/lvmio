"""LabVIEW's reader on unusual layouts, and what it writes back after reading a file."""

from __future__ import annotations

import json
import math
from pathlib import Path

from lvmio import format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
RESULTS = json.loads((HERE / "read_results.json").read_text(encoding="utf-8"))
CRLF, TAB = "\r\n", "\t"


def _relay_line(name: str, key: str) -> list[str]:
    lines = (HERE / "relay" / name).read_bytes().decode("cp1252").split(CRLF)
    return next(line for line in lines if line.startswith(key + TAB)).split(TAB)[1:]


def test_a_row_of_empty_cells_is_a_row_of_missing_samples() -> None:
    last = read_lvm(HERE / "read" / "empty_last_row.lvm").segments[0]
    assert [c.data[:2] for c in last] == [[1.0, 2.0], [3.0, 4.0]]
    assert all(math.isnan(c.data[2]) for c in last)
    middle = read_lvm(HERE / "read" / "empty_middle_row.lvm").segments[0]
    assert [c.data[0] for c in middle] == [1.0, 3.0] and math.isnan(middle.channels[0].data[1])
    assert [c.data[2] for c in middle] == [2.0, 4.0]
    assert RESULTS["read/empty_middle_row.lvm"][0]["channels"] == [
        [1.0, "NaN", 0.0],
        [3.0, "NaN", 0.0],
    ]


def test_a_channels_key_with_a_trailing_space_reads_nothing_in_labview() -> None:
    assert RESULTS["read/channels_key_with_space.lvm"][0] == {
        "error": 0,
        "channels": [],
        "eof": True,
        "comment": "",
    }
    assert read_lvm(HERE / "read" / "channels_key_with_space.lvm").segments[0].names == ["A", "B"]


def test_labview_takes_a_blank_or_text_delta_x_as_zero() -> None:
    for name in ("blank_delta_x.lvm", "text_delta_x.lvm"):
        assert _relay_line(name, "Delta_X")[:2] == ["0,000000", "0,000000"]
    assert read_lvm(HERE / "read" / "blank_delta_x.lvm").segments[0].channels[0].delta_x == 1.0


def test_labview_shifts_units_past_an_empty_unit_cell() -> None:
    ours = read_lvm(HERE / "read" / "lvmio_unit_gap.lvm").segments[0]
    assert [c.unit for c in ours] == ["", "A", "V"]
    assert _relay_line("lvmio_unit_gap.lvm", "Y_Unit_Label")[:3] == ["A", "V", ""]


def test_a_labview_file_with_units_reads_and_survives_a_rewrite() -> None:
    raw = (HERE / "relay" / "lvmio_units.lvm").read_bytes().decode("cp1252")
    lvm = parse_lvm(raw)
    assert [c.unit for c in lvm.segments[0]] == ["V", "A"]
    assert format_lvm(lvm) == raw


def test_labview_writes_a_notes_line_before_channels_and_lvmio_reads_past_it() -> None:
    raw = (HERE / "relay" / "lvmio_unit_gap.lvm").read_bytes().decode("cp1252")
    assert any(line.startswith("Notes" + TAB) for line in raw.split(CRLF))
    assert parse_lvm(raw).segments[0].names == ["C0", "Amp", "V"]

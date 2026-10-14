"""Contract test: the complete, documented promise of every public name.

Every exported symbol is exercised end to end against the hand-made
LabVIEW-layout fixtures committed under ``tests/fixtures``. If a public behaviour changes, a
claim here breaks.
"""

import importlib.resources
import math
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import lvmio
from lvmio import (
    Channel,
    LvmError,
    LvmFile,
    Segment,
    format_lvm,
    parse_lvm,
    read_lvm,
    write_lvm,
)

FIXTURES = Path(__file__).parent / "fixtures"

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "Channel",
    "LvmError",
    "LvmFile",
    "Segment",
    "format_lvm",
    "parse_lvm",
    "read_lvm",
    "write_lvm",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvmio.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvmio.__all__:
        assert hasattr(lvmio, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvmio.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvmio").joinpath("py.typed").is_file()


def test_read_lvm_parses_a_file() -> None:
    lvm = read_lvm(FIXTURES / "short.lvm")
    assert isinstance(lvm, LvmFile)
    assert lvm.operator == "lvmio"
    assert lvm.separator == "Tab"
    assert lvm.decimal_separator == ","
    assert lvm.x_columns == "No"
    names = lvm.segments[0].names
    assert names == ["Load (Cell A)", "Accel (Frame)"]
    assert lvm.segments[0].channels[0].data[0] == pytest.approx(0.5)


def test_parse_lvm_matches_read_lvm_on_the_same_bytes() -> None:
    path = FIXTURES / "comma_separator.lvm"
    from_text = parse_lvm(path.read_text(encoding="utf-8"))
    from_path = read_lvm(path)
    assert from_text == from_path


def test_x_columns_no_file_reads_the_real_channels() -> None:
    # X_Columns=No files still carry an empty leading X column; the reader
    # must skip it, not read channel zero from it.
    lvm = read_lvm(FIXTURES / "short.lvm")
    excitation = lvm.segments[0]["Load (Cell A)"]
    assert len(excitation) == 10
    assert excitation.data[0] == pytest.approx(0.5)
    assert not any(math.isnan(v) for v in excitation.data)


def test_empty_fields_become_nan() -> None:
    lvm = read_lvm(FIXTURES / "with_empty_fields.lvm")
    # The unconnected channel's Samples count is 0: its empty cells are padding, as LabVIEW
    # reads it. An empty cell within a channel's count is a missing sample: NaN.
    assert lvm.segments[0]["Spare"].data == []
    text = format_lvm([Channel("A", [1.0, math.nan, 3.0]), Channel("B", [4.0])])
    assert math.isnan(parse_lvm(text).segments[0]["A"].data[1])
    assert parse_lvm(text).segments[0]["B"].data == [4.0]
    connected = lvm.segments[0]["Dev1/ai0"]
    assert connected.data[0] == pytest.approx(-0.02)


def test_channel_is_frozen_iterable_and_sized() -> None:
    channel = Channel("V", [1.0, 2.0, 3.0], unit="V", x0=0.5, delta_x=0.25)
    assert len(channel) == 3
    assert list(channel) == [1.0, 2.0, 3.0]
    assert channel.time_axis() == [0.5, 0.75, 1.0]
    with pytest.raises(FrozenInstanceError):  # frozen dataclass rejects mutation
        channel.name = "W"  # type: ignore[misc]


def test_segment_is_a_mapping_and_sequence_of_channels() -> None:
    segment = Segment([Channel("A", [1.0]), Channel("B", [2.0, 3.0])])
    assert len(segment) == 2
    assert segment.names == ["A", "B"]
    assert segment.samples == [1, 2]
    assert "A" in segment and "Z" not in segment
    assert segment["B"].data == [2.0, 3.0]
    assert segment.get("Z") is None
    assert [c.name for c in segment] == ["A", "B"]
    with pytest.raises(KeyError):
        segment["missing"]


def test_lvmfile_iterates_segments_and_reports_multi_headings() -> None:
    one = LvmFile(segments=[Segment([Channel("A", [1.0])])])
    assert len(one) == 1
    assert one.multi_headings is False
    two = LvmFile(segments=[Segment([Channel("A", [1.0])]), Segment([Channel("B", [2.0])])])
    assert two.multi_headings is False
    assert [len(seg) for seg in two] == [1, 1]
    # The writer marks a file with several segments, and the reader reports the field.
    assert "Multi_Headings\tYes\r\n" in lvmio.format_lvm(two)
    assert parse_lvm(lvmio.format_lvm(two)).multi_headings is True
    assert parse_lvm(lvmio.format_lvm(one)).multi_headings is False
    assert parse_lvm(lvmio.format_lvm(LvmFile(one.segments, multi_headings=True))).multi_headings


def test_write_lvm_round_trips_every_input_shape(tmp_path: Path) -> None:
    out = tmp_path / "r.lvm"
    write_lvm(out, {"x": [1.0, 2.0], "y": [3.0, 4.0]})
    assert read_lvm(out).segments[0].names == ["x", "y"]

    write_lvm(out, [Channel("Only", [5.0, 6.0])], separator="Comma")
    back = read_lvm(out)
    assert back.separator == "Comma"
    assert back.segments[0]["Only"].data == [5.0, 6.0]

    write_lvm(out, Segment([Channel("S", [7.0])]), operator="rig")
    assert read_lvm(out).operator == "rig"


def test_write_lvm_leaves_a_nan_sample_empty_and_reads_it_back(tmp_path: Path) -> None:
    out = tmp_path / "gap.lvm"
    write_lvm(out, [Channel("G", [1.0, math.nan, 3.0])])
    back = read_lvm(out).segments[0]["G"]
    assert back.data[0] == 1.0
    assert math.isnan(back.data[1])
    assert back.data[2] == 3.0


def test_lvmerror_is_raised_on_foreign_and_malformed_input(tmp_path: Path) -> None:
    assert issubclass(LvmError, ValueError)
    with pytest.raises(LvmError):
        parse_lvm("not an lvm file\n")
    bad = tmp_path / "bad.lvm"
    bad.write_text(
        "LabVIEW Measurement\t\n***End_of_Header***\t\n\nChannels\t1\n"
        "***End_of_Header***\t\nX_Value\tA\tComment\n0\tnope\n",
        encoding="utf-8",
    )
    with pytest.raises(LvmError):
        read_lvm(bad)

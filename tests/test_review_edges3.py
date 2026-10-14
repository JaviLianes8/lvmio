"""Contracts from the second API and docs review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lvmio import Channel, LvmFile, Segment, format_lvm, parse_lvm
from lvmio._cli_output import _header_fields


def test_a_channel_keeps_any_iterable_as_a_list() -> None:
    channel = Channel("a", (x for x in [1.0, 2.0]))  # type: ignore[arg-type]
    assert channel.data == [1.0, 2.0] and len(channel) == 2
    assert format_lvm([channel]) == format_lvm([channel])
    assert Channel("a", (1.0, 2.0)) == Channel("a", [1.0, 2.0])  # type: ignore[arg-type]


@pytest.mark.parametrize("text", [" lead", "trail ", "a" + chr(0xA0)])
def test_a_description_with_blanks_at_either_end_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="description cannot start or end with blanks"):
        format_lvm(LvmFile([Segment([Channel("V", [1.0])])], description=text))


def test_an_empty_x_dimension_is_written_and_read_back() -> None:
    text = format_lvm([Channel("A", [1.0], x_dimension=""), Channel("B", [2.0])])
    assert [c.x_dimension for c in parse_lvm(text).segments[0]] == ["", "Time"]


def test_a_non_finite_x0_is_refused() -> None:
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="x0 must be finite"):
            format_lvm([Channel("A", [1.0], x0=value)])


def test_the_header_command_shows_the_description() -> None:
    lvm = parse_lvm(format_lvm(LvmFile([Segment([Channel("V", [1.0])])], description="run 7")))
    fields = _header_fields(lvm)
    assert fields["description"] == "run 7"
    json.dumps(fields)


def test_a_large_x0_at_full_precision_stays_one_segment() -> None:
    for x0, dx in ((3.8e9, 1e-6), (3.8e9, 1e-7), (1e12, 1e-4), (3786912000.5, 1e-6)):
        text = format_lvm([Channel("V", [0.0] * 2000, x0=x0, delta_x=dx)], precision=17)
        assert len(parse_lvm(text)) == 1


def test_channels_of_different_lengths_read_back_at_their_own_length() -> None:
    lvm = LvmFile([Segment([Channel("A", [1.0, 2.0, 3.0]), Channel("B", [9.0])])])
    back = parse_lvm(format_lvm(lvm))
    assert [c.data for c in back.segments[0]] == [[1.0, 2.0, 3.0], [9.0]]
    assert format_lvm(back) == format_lvm(lvm)


def test_segments_and_files_keep_their_containers_as_lists() -> None:
    channel = Channel("A", [1.0])
    assert Segment((channel,)) == Segment([channel])  # type: ignore[arg-type]
    segment = Segment(c for c in [channel])  # type: ignore[arg-type]
    assert LvmFile((segment,)) == LvmFile([segment])  # type: ignore[arg-type]
    assert parse_lvm(format_lvm(segment)).segments[0].names == ["A"]


def test_a_non_finite_delta_x_is_refused() -> None:
    with pytest.raises(ValueError, match="delta_x must be finite"):
        format_lvm([Channel("A", [1.0], delta_x=float("inf"))])


def test_the_header_text_escapes_a_description_with_a_line_break(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    from lvmio._cli import main

    path = tmp_path / "d.lvm"
    lvm = LvmFile([Segment([Channel("V", [1.0])])], description="line1\nsegments: 99")
    path.write_bytes(format_lvm(lvm).encode("ascii"))
    assert main(["header", str(path)]) == 0
    out = capsys.readouterr().out
    assert "description: line1" + chr(92) + "0Asegments: 99" in out
    assert out.count("segments:") == 2

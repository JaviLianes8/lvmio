"""Contracts from the second API and docs review."""

from __future__ import annotations

import json

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

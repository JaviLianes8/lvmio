"""The X axis of LabVIEW captures: the three X column layouts and X increments."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from lvmio import Channel, format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
CRLF, TAB = "\r\n", "\t"


def _rewrite(name: str) -> list[tuple[str, str]]:
    raw = (HERE / name).read_bytes().decode("ascii")
    again = format_lvm(parse_lvm(raw))
    return [(a, b) for a, b in zip(raw.split(CRLF), again.split(CRLF), strict=True) if a != b]


def test_an_increment_that_fits_six_decimals_survives_a_rewrite() -> None:
    assert _rewrite("delta_x_quarter.lvm") == []
    assert read_lvm(HERE / "delta_x_quarter.lvm").segments[0].channels[0].delta_x == 0.25


def test_labview_writes_x_from_the_true_increment_but_stores_it_rounded() -> None:
    channel = read_lvm(HERE / "delta_x_2048hz.lvm").segments[0].channels[0]
    assert channel.delta_x == 0.000488
    assert len(channel.data) == 3000
    changed = _rewrite("delta_x_2048hz.lvm")
    assert len(changed) == 2998
    for before, after in changed:
        assert before.split(TAB)[1:] == after.split(TAB)[1:]
    assert ("0,000977" + TAB + "2,000000", "0,000976" + TAB + "2,000000") in changed


def test_x_cells_at_near_ties_differ_by_one_unit_in_the_last_decimal() -> None:
    changed = _rewrite("delta_x_1e-7.lvm")
    assert len(changed) == 14
    for before, after in changed:
        assert before.split(TAB)[1:] == after.split(TAB)[1:]
        ours, theirs = (Decimal(line.split(TAB)[0].replace(",", ".")) for line in (after, before))
        assert abs(ours - theirs) == Decimal("0.000001")


def test_delta_x_keeps_six_decimals_at_a_low_precision() -> None:
    text = format_lvm([Channel("V", [1.0, 2.0], delta_x=0.25)], precision=0)
    assert "Delta_X" + TAB + "0.250000" + TAB + CRLF in text
    assert parse_lvm(text).segments[0].channels[0].delta_x == 0.25


def test_every_x_columns_layout_reads_the_same_channels() -> None:
    for name, layout in [
        ("x_columns_no", "No"),
        ("x_columns_one", "One"),
        ("x_columns_multi", "Multi"),
    ]:
        lvm = read_lvm(HERE / f"{name}.lvm")
        assert lvm.x_columns == layout
        assert [c.name for c in lvm.segments[0]] == ["Untitled", "Untitled 1"]
        assert [c.data for c in lvm.segments[0]] == [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]
        assert lvm.segments[0].channels[1].time_axis() == [0.0, 1.0, 2.0]


def test_labview_spells_some_x0_values_one_unit_off_and_both_read_the_same() -> None:
    raw = (HERE / "x0_offsets.lvm").read_bytes().decode("ascii")
    lvm = parse_lvm(raw)
    assert len(lvm) == 60
    assert any(seg.channels[0].x0 != 0 for seg in lvm)
    changed = _rewrite("x0_offsets.lvm")
    x0_lines = [(a, b) for a, b in changed if a.startswith("X0" + TAB)]
    assert len(x0_lines) == 2
    for before, after in x0_lines:
        assert before != after
        theirs, ours = (float(line.split(TAB)[1].replace(",", ".")) for line in (before, after))
        assert theirs == ours
    for before, after in changed:
        if not before.startswith("X0" + TAB):
            assert before.split(TAB)[1:] == after.split(TAB)[1:]

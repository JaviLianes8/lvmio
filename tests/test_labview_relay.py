"""What LabVIEW's reader keeps of X dimensions and X0, seen through LabVIEW writing it back."""

from __future__ import annotations

from pathlib import Path

from lvmio import format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
CRLF, TAB = "\r\n", "\t"


def _raw(name: str) -> str:
    return (HERE / name).read_bytes().decode("cp1252")


def _line(name: str, key: str) -> list[str]:
    return next(x for x in _raw(name).split(CRLF) if x.startswith(key + TAB)).split(TAB)[1:]


def test_labview_keeps_only_the_time_and_frequency_dimensions() -> None:
    ours = read_lvm(HERE / "read" / "lvmio_dimensions.lvm").segments[0]
    assert [c.x_dimension for c in ours] == ["Time", "Frequency", "Other", "frequency"]
    assert _line("relay/lvmio_dimensions.lvm", "X_Dimension")[:4] == [
        "Time",
        "Frequency",
        "",
        "Frequency",
    ]
    relayed = parse_lvm(_raw("relay/lvmio_dimensions.lvm"))
    assert [c.x_dimension for c in relayed.segments[0]] == ["Time", "Frequency", "", "Frequency"]
    assert format_lvm(relayed) == _raw("relay/lvmio_dimensions.lvm")


def test_labview_holds_x0_as_a_timestamp() -> None:
    ours = read_lvm(HERE / "read" / "lvmio_x0.lvm").segments[0]
    assert [c.x0 for c in ours] == [1.23e-9, 2.5e-7, 1e-20, 0.125, 1e19, -3.5]
    theirs = [c.x0 for c in parse_lvm(_raw("relay/lvmio_x0.lvm")).segments[0]]
    assert theirs[3] == 0.125 and theirs[5] == -3.5
    assert theirs[0] != 1.23e-9 and abs(theirs[0] - 1.23e-9) < 1e-18
    assert theirs[2] == 0.0
    assert theirs[4] < 0

"""Hand-written layouts that probe how LabVIEW's reader treats unusual header lines."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from _hand_inputs import _head, _seg

TAB = chr(9)
# Line indexes in the base file: 0 to 12 the file header, then the segment header.
CHANNELS, X0, DELTA_X, COLUMNS = 13, 19, 20, 22


def _base(x_columns: str = "One") -> list[str]:
    rows = [["0", "1", "3"], ["1", "2", "4"]]
    if x_columns == "No":
        rows = [["", "1", "3"], ["", "2", "4"]]
    return _head(xcol=x_columns) + _seg(["A", "B"], ["", ""], "1", rows)


def _edited(change: Callable[[list[str]], None], x_columns: str = "One") -> list[str]:
    lines = _base(x_columns)
    change(lines)
    return lines


def _three_rows(lines: list[str], where: int) -> None:
    """Add a row whose cells are all empty, and count it in Samples."""
    lines.insert(where, TAB + TAB)
    lines[CHANNELS + 1] = "Samples" + TAB + "3" + TAB + "3"


def _per_channel(first: str, second: str, cells: list[list[str]]) -> list[str]:
    """Two channels over five rows with their own Samples counts."""
    rows = [[str(i), *pair] for i, pair in enumerate(cells)]
    lines = _head() + _seg(["A", "B"], ["", ""], "1", rows)
    lines[CHANNELS + 1] = "Samples" + TAB + first + TAB + second
    return lines


def layouts() -> dict[str, list[str]]:
    """File name to lines (joined with CRLF by the caller)."""
    return {
        "blank_in_file_header.lvm": _edited(lambda ls: ls.insert(3, "")),
        "spaces_line_in_file_header.lvm": _edited(lambda ls: ls.insert(3, "   ")),
        "blank_in_segment_header.lvm": _edited(lambda ls: ls.insert(X0, "")),
        "blank_before_column_line.lvm": _edited(lambda ls: ls.insert(COLUMNS, "")),
        "empty_last_row.lvm": _edited(lambda ls: _three_rows(ls, -1), "No"),
        "empty_middle_row.lvm": _edited(lambda ls: _three_rows(ls, -2), "No"),
        "no_x0_line.lvm": _edited(lambda ls: ls.pop(X0)),
        "no_date_time_lines.lvm": _edited(
            lambda ls: ls.__delitem__(slice(CHANNELS + 2, CHANNELS + 4))
        ),
        "no_delta_x_line.lvm": _edited(lambda ls: ls.pop(DELTA_X)),
        "samples_per_channel_full.lvm": _per_channel("2", "3", [["1", "11"]] * 5),
        "samples_per_channel_padding.lvm": _per_channel(
            "2", "5", [["1", "11"], ["2", "12"], ["", "13"], ["", "14"], ["", "15"]]
        ),
        "blank_delta_x.lvm": _edited(lambda ls: ls.__setitem__(DELTA_X, "Delta_X" + TAB + TAB)),
        "text_delta_x.lvm": _edited(
            lambda ls: ls.__setitem__(DELTA_X, "Delta_X" + TAB + "abc" + TAB + "abc")
        ),
        "x0_key_with_space.lvm": _edited(lambda ls: ls.__setitem__(X0, "X0 " + ls[X0][2:])),
        "channels_key_with_space.lvm": _edited(
            lambda ls: ls.__setitem__(CHANNELS, "Channels " + ls[CHANNELS][8:])
        ),
    }


def _multi_two_channels() -> list[str]:
    """X_Columns Multi with two channels whose Samples count is above the two rows."""
    head = _head(xcol="Multi")
    cells = [
        ["Channels", "2", "", "", ""],
        ["Samples", "5", "", "5", ""],
        ["Date", "2026/10/14", "", "2026/10/14", ""],
        ["Time", "10:00:00", "", "10:00:00", ""],
        ["X_Dimension", "Time", "", "Time", ""],
        ["X0", "0", "", "0", ""],
        ["Delta_X", "1", "", "1", ""],
        ["***End_of_Header***", "", "", "", ""],
        ["X_Value", "A", "X_Value", "B", "Comment"],
        ["0", "1", "0", "3"],
        ["1", "2", "1", "4"],
    ]
    return head + [TAB.join(row) for row in cells] + [""]


def write_layouts(folder: Path) -> dict[str, str]:
    made = {}
    shapes = {**layouts(), "samples_more_multi_two_channels.lvm": _multi_two_channels()}
    for name, lines in shapes.items():
        (folder / name).write_bytes("\r\n".join(lines).encode("utf-8"))
        made[f"read/{name}"] = "hand-written input for LabVIEW's reader (scripts/_hand_layouts.py)"
    bom = folder / "byte_order_mark.lvm"
    bom.write_bytes(chr(0xFEFF).encode("utf-8") + "\r\n".join(_base()).encode("utf-8"))
    made["read/byte_order_mark.lvm"] = "hand-written input for LabVIEW's reader, UTF-8 BOM first"
    return made

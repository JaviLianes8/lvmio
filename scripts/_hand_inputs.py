"""Hand-written .lvm files given to LabVIEW's reader."""

from __future__ import annotations

from pathlib import Path

from _cases import TOKENS


def _head(
    sep: str = "Tab", dec: str = ".", multi: str = "No", xcol: str = "One", d: str = "\t"
) -> list[str]:
    keys = [
        ("Writer_Version", "2"),
        ("Reader_Version", "2"),
        ("Separator", sep),
        ("Decimal_Separator", dec),
        ("Multi_Headings", multi),
        ("X_Columns", xcol),
        ("Time_Pref", "Relative"),
        ("Operator", "tester"),
        ("Date", "2026/10/14"),
        ("Time", "10:00:00"),
    ]
    return (
        ["LabVIEW Measurement" + d] + [k + d + v for k, v in keys] + ["***End_of_Header***" + d, ""]
    )


def _seg(
    names: list[str],
    units: list[str],
    dx: str,
    rows: list[list[str]],
    d: str = "\t",
    columns: list[str] | None = None,
) -> list[str]:
    n = len(names)
    out = [
        d.join(["Channels", str(n)] + [""] * n),
        d.join(["Samples"] + [str(len(rows))] * n),
        d.join(["Date"] + ["2026/10/14"] * n),
        d.join(["Time"] + ["10:00:00"] * n),
        d.join(["Y_Unit_Label", *units]),
        d.join(["X_Dimension"] + ["Time"] * n),
        d.join(["X0"] + ["0"] * n),
        d.join(["Delta_X"] + [dx] * n),
        d.join(["***End_of_Header***"] + [""] * n),
        d.join(columns if columns is not None else ["X_Value", *names, "Comment"]),
    ]
    return out + [d.join(r) for r in rows] + [""]


def write_hand_inputs(folder: Path) -> dict[str, str]:
    """Hand-written files for LabVIEW's reader; returns file name to description."""
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "tab_one_x.lvm": _head()
        + _seg(
            ["Volt", "Amp"],
            ["V", "A"],
            "0.5",
            [["0.0", "1.25", "-2"], ["0.5", "3.5", "4e-3"], ["1.0", "-0.000125", "1E+3"]],
        ),
        "no_x_empty_cells.lvm": _head(xcol="No")
        + _seg(
            ["A", "B", "C"],
            ["", "", ""],
            "1",
            [["", "1", "", "7"], ["", "2", "5", ""], ["", "", "6", "9"]],
        ),
        "comma_separator.lvm": _head(sep="Comma", d=",")
        + _seg(["P", "Q"], ["", ""], "0.1", [["0", "1.5", "2.5"], ["0.1", "3.5", "-4.5"]], d=","),
        "decimal_comma.lvm": _head(dec=",")
        + _seg(
            ["P", "Q"], ["", ""], "0,1", [["0", "1,5", "2,5E-3"], ["0,1", "-3,25", "1000000,5"]]
        ),
        "two_segments.lvm": _head(multi="Yes")
        + _seg(["A", "B"], ["V", "V"], "1", [["0", "1", "2"], ["1", "3", "4"]])
        + _seg(["C"], ["mA"], "0.25", [["5", "9.5"], ["5.25", "10.5"], ["5.5", "11.5"]]),
        "short_row.lvm": _head()
        + _seg(["A", "B", "C"], ["", "", ""], "1", [["0", "1", "2", "3"], ["1", "4"]]),
        "no_x_value_column.lvm": _head(xcol="No")
        + _seg(["A", "B"], ["", ""], "1", [["1", "2"], ["3", "4"]], columns=["A", "B", "Comment"]),
        "blank_line_in_rows.lvm": _head() + _seg(["A"], [""], "1", [["0", "1"], [], ["2", "5"]]),
        "comment_cells.lvm": _head()
        + _seg(["A"], [""], "1", [["0", "1", "com", "99", "100"], ["1", "2"]]),
        "period_cell_in_comma_file.lvm": _head(dec=",")
        + _seg(["A"], [""], "1", [["0", "1,5"], ["1", "+.5e+3"]]),
        "comment_escapes.lvm": _head()
        + _seg(["A"], [""], "1", [["0", "1", "a\\41b\\09c\\5Cd\\zz\\4"], ["1", "2"]]),
    }
    made = {}
    for i, token in enumerate(TOKENS):
        files[f"token_{i:02d}.lvm"] = (
            _head() + _seg(["S"], [""], "1", [["0", "1"], ["1", token]])[:-1]
        )
    for name, lines in files.items():
        (folder / name).write_bytes("\r\n".join(lines).encode("utf-8"))
        made[f"read/{name}"] = "hand-written input for LabVIEW's reader (scripts/_cases.py)"
    return made

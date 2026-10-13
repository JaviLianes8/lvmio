"""Write the hand-made .lvm fixtures in tests/fixtures.

Every value is generated here from a formula; nothing is copied from another file. Each
fixture exercises one layout real LabVIEW output uses:

* ``short.lvm``: tab separator, decimal comma, ``X_Columns`` No (an empty leading X column).
* ``comments_on_some_rows.lvm``: the same data with a comment on two rows.
* ``comma_separator.lvm``: comma separator, decimal point, one X column, trailing commas.
* ``with_empty_fields.lvm``: a ``Notes`` line and channels whose fields are all empty.

    python scripts/make_lvm_fixtures.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
DESCRIPTION = "Hand-made lvmio test fixture, written by scripts/make_lvm_fixtures.py"
END = "***End_of_Header***"


def _file_header(sep: str, decimal: str, multi: str, x_columns: str, time: str) -> list[str]:
    rows = [
        ["LabVIEW Measurement", ""],
        ["Writer_Version", "2"],
        ["Reader_Version", "2"],
        ["Separator", "Tab" if sep == "\t" else "Comma"],
        ["Decimal_Separator", decimal],
        ["Multi_Headings", multi],
        ["X_Columns", x_columns],
        ["Time_Pref", "Absolute"],
        ["Operator", "lvmio"],
        ["Description", DESCRIPTION],
        ["Date", "2026/10/13"],
        ["Time", time],
        [END, ""],
        ["", ""],
    ]
    return [sep.join(row) for row in rows]


def _num(value: float, decimal: str) -> str:
    return f"{value:.6f}".replace(".", decimal)


def _short(comments: dict[int, str]) -> str:
    sep, dec = "\t", ","
    names, units = ["Load (Cell A)", "Accel (Frame)"], ["Newtons", "m/s^2"]
    load = [0.5 + 0.4 * math.sin(0.7 * i) for i in range(10)]
    accel = [1.2 + 0.02 * math.cos(0.9 * i) for i in range(10)]
    lines = _file_header(sep, dec, "Yes", "No", "10:15:30,5")
    lines += [
        sep.join(["Channels", "2", "", ""]),
        sep.join(["Samples", "10", "10", ""]),
        sep.join(["Date", "2026/10/13", "2026/10/13", ""]),
        sep.join(["Time", "10:15:31,25", "10:15:31,25", ""]),
        sep.join(["Y_Unit_Label", *units, ""]),
        sep.join(["X_Dimension", "Time", "Time", ""]),
        sep.join(["X0", "0,0000000000000000E+0", "0,0000000000000000E+0", ""]),
        sep.join(["Delta_X", "2,500000E-4", "2,500000E-4", ""]),
        sep.join([END, "", "", ""]),
        sep.join(["X_Value", *names, "Comment"]),
    ]
    for i in range(10):
        row = ["", _num(load[i], dec), _num(accel[i], dec)]
        lines.append(sep.join(row + ([comments[i]] if i in comments else [])))
    return "\n".join(lines) + "\n"


def _comma() -> str:
    sep, dec = ",", "."
    names = ["inlet", "outlet", "chamber", "T1"]
    lines = _file_header(sep, dec, "No", "One", "08:00:00.125")
    lines += [
        sep.join(["Channels", "4", "", "", "", ""]),
        sep.join(["Samples", *["4"] * 4, ""]),
        sep.join(["Date", *["2026/10/13"] * 4, ""]),
        sep.join(["Time", *["08:00:00.125"] * 4, ""]),
        sep.join(["Y_Unit_Label", *["Volts"] * 4, ""]),
        sep.join(["X_Dimension", *["Time"] * 4, ""]),
        sep.join(["X0", *["0.0000000000000000E+0"] * 4, ""]),
        sep.join(["Delta_X", *["5.000000E-6"] * 4, ""]),
        sep.join([END, "", "", "", "", ""]),
        sep.join(["X_Value", *names, "Comment"]),
    ]
    for i in range(4):
        values = [0.001 * (i + 1) * (c + 1) - 0.004 for c in range(3)] + [0.25 + 0.0005 * i]
        lines.append(
            sep.join([f"{5e-6 * i:.6E}" if i else "0.000000", *(_num(v, dec) for v in values)])
        )
    return "\n".join(lines) + "\n"


def _empty_fields() -> str:
    sep, dec = "\t", "."
    names = ["Dev1/ai0", "Dev1/ai1", "Spare", "Spare 1", "Spare 2", "Spare 3", "Dev1/ai0 1"]
    lines = [line.rstrip("\t") for line in _file_header(sep, dec, "No", "One", "16:20:00.5")]
    lines += [
        sep.join(["Notes", "X values are valid only for Dev1/ai0"]),
        sep.join(["Channels", "7"]),
        sep.join(["Samples", "8", "8", "0", "0", "0", "0", "8"]),
        sep.join(["Date", *["2026/10/13"] * 7]),
        sep.join(["Time", *["16:20:01.5"] * 7]),
        sep.join(["X_Dimension", *["Time"] * 7]),
        sep.join(["X0", *["0.0000000000000000E+0"] * 7]),
        sep.join(["Delta_X", "0.002000", "0.002000", *["1.000000"] * 4, "0.002000"]),
        END,
        sep.join(["X_Value", *names, "Comment"]),
    ]
    for i in range(8):
        signal = _num(0.01 * math.sin(i) - 0.02, dec)
        supply = _num(5.0 + 0.001 * (i % 3), dec)
        lines.append(sep.join([_num(0.002 * i, dec), signal, supply, "", "", "", "", signal]))
    return "\n".join(lines) + "\n"


def main() -> None:
    files = {
        "short.lvm": _short({}),
        "comments_on_some_rows.lvm": _short({2: "tap test", 6: "cable moved"}),
        "comma_separator.lvm": _comma(),
        "with_empty_fields.lvm": _empty_fields(),
    }
    for name, text in files.items():
        (OUT / name).write_bytes(text.encode("utf-8"))


if __name__ == "__main__":
    main()

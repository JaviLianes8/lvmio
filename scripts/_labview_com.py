"""LabVIEW 2026 measurement-file VIs over its ActiveX server, for capture_labview.py."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import win32com.client.dynamic as dynamic  # type: ignore[import-not-found]

EXPRESS = r"C:\Program Files\National Instruments\LabVIEW 2026\vi.lib\express" + "\\"
TO_DDT = r"express signal manip\ConverttoDDTBlocks.llb\2D Dbl to DDT.vi"
FROM_DDT = r"express signal manip\ConvertfromDDTBlocks.llb\DDT to 2D Dbl.vi"
WRITE = r"express output\ExFileWriteBlock.llb\Ex_Inst_Write LabVIEW Measurement File.vi"
WORKER = r"express output\ExFileWriteBlock.llb\ex_subFileWrite.vi"
READ = r"express input\ExFileReadBlock.llb\Ex_Inst_Read LabVIEW Measurement File.vi"


class LabVIEW:
    def __init__(self) -> None:
        self.app = dynamic.Dispatch("LabVIEW.Application")
        self.version = str(self.app.Version)

    def vi(self, path: str) -> Any:
        ref = self.app.GetVIReference(EXPRESS + path, "", False, 0)
        ref._FlagAsMethod("GetControlValue", "SetControlValue", "Run")
        return ref

    def signals(self, rows: list[list[float]]) -> Any:
        conv = self.vi(TO_DDT)
        conv.SetControlValue("2D Array", rows)
        conv.Run(False)
        return conv.GetControlValue("Dynamic Data Type")


def express(lv: LabVIEW, path: Path, rows: list[list[float]], comment: str = "") -> None:
    vi = lv.vi(WRITE)
    vi.SetControlValue("Signals", lv.signals(rows))
    vi.SetControlValue("Filename", str(path))
    vi.SetControlValue("Comment", comment)
    vi.Run(False)
    _check(vi.GetControlValue("error out"))


def worker(lv: LabVIEW, path: Path, passes: list[dict[str, Any]], x_columns: int) -> None:
    """Run the express VI's worker once per pass in one session, appending segments."""
    vi = lv.vi(WORKER)
    for index, step in enumerate(passes):
        vi.SetControlValue("Signals", lv.signals(step["rows"]))
        vi.SetControlValue("File Path in", str(path))
        vi.SetControlValue("Static File Path in", str(path))
        vi.SetControlValue("x_columns", x_columns)
        vi.SetControlValue("overwrite_mode", 2)
        vi.SetControlValue("Comment", step.get("comment", ""))
        later = bool(step.get("later_session", False))
        vi.SetControlValue("Reset", index == 0 and not later)
        vi.SetControlValue("Simulate Non-First Call", later)
        if "decimal" in step:
            params = list(vi.GetControlValue("file params"))
            params[3] = step["decimal"]
            vi.SetControlValue("file params", tuple(params))
        vi.Run(False)
        _check(vi.GetControlValue("error out"))


def read(lv: LabVIEW, path: Path, limit: int = 6) -> list[dict[str, Any]]:
    """What LabVIEW's reader returns, one call per data set, until it reports EOF."""
    vi, conv = lv.vi(READ), lv.vi(FROM_DDT)
    vi.SetControlValue("Filename", str(path))
    results = []
    for index in range(limit):
        vi.SetControlValue("Reset", index == 0)
        vi.Run(False)
        error = vi.GetControlValue("error out")
        conv.SetControlValue("Dynamic Data Type", vi.GetControlValue("Signals"))
        conv.Run(False)
        rows = [[_jsonable(v) for v in row] for row in conv.GetControlValue("Array")]
        results.append(
            {
                "error": int(error[1]),
                "channels": rows,
                "eof": bool(vi.GetControlValue("EOF?")),
                "comment": str(vi.GetControlValue("Comment")),
            }
        )
        if results[-1]["eof"] or error[0]:
            break
        if index and results[-1]["channels"] == results[0]["channels"]:
            results[-1] = {"repeats_first": True}
            break
    return results


def _check(error: Any) -> None:
    if error[0]:
        raise RuntimeError(f"LabVIEW error {error[1]}: {error[2]}")


def _jsonable(value: float) -> float | str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    return value

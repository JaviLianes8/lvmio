"""Files written by this checkout of lvmio, for LabVIEW's reader to read back."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lvmio import Channel, LvmFile, Segment, write_lvm

# Cells LabVIEW's reader turns into a double one unit in the last place away from the
# correctly rounded value of the text.
ULP_CELLS = [0.011227, -519.782038, 4037235.244863, -8.633024e-6, 7.801666e104, -1.034e241]


def write_inputs(folder: Path) -> dict[str, str]:
    """Write every case into ``folder`` and return file name to description."""
    volts = Channel("Volt", [1.5, -2.25, 1e-9, 1e300, math.nan], unit="V", x0=0.5, delta_x=0.25)
    amps = Channel("Amp", [0.125, 4e-5, -7.0], unit="A", x0=0.5, delta_x=0.25)
    other = Channel("Late", [10.0, 20.0, 30.0], unit="s", x0=3.0, delta_x=2.0)
    cases = {
        "lvmio_one.lvm": (LvmFile([Segment([volts, amps])]), {}),
        "lvmio_no.lvm": (LvmFile([Segment([volts, amps])], x_columns="No"), {}),
        "lvmio_multi.lvm": (LvmFile([Segment([volts, other])], x_columns="Multi"), {}),
        "lvmio_comma.lvm": (LvmFile([Segment([volts, amps])], separator="Comma"), {}),
        "lvmio_decimal_comma.lvm": (LvmFile([Segment([volts, amps])], decimal_separator=","), {}),
        "lvmio_segments.lvm": (
            LvmFile(
                [
                    Segment([amps], comment="first"),
                    Segment([volts, other], comment="second"),
                    Segment([other]),
                ]
            ),
            {},
        ),
        "lvmio_cp1252.lvm": (
            LvmFile([Segment([Channel("Temperatura \u00b5", [21.5, 22.0], unit="\u00b0C")])]),
            {"operator": "Jos\u00e9", "encoding": "cp1252"},
        ),
        "lvmio_precision.lvm": (LvmFile([Segment([volts, amps])]), {"precision": 9}),
        "lvmio_utf8_comment.lvm": (
            LvmFile([Segment([amps], comment="caf" + chr(0xE9) + " " + chr(0x20AC))]),
            {},
        ),
        "lvmio_ulp.lvm": (
            LvmFile([Segment([Channel("U", ULP_CELLS)])]),
            {},
        ),
        "lvmio_escaped_comment.lvm": (
            LvmFile([Segment([amps], comment="a" + chr(9) + "b" + chr(92) + "c" + chr(10) + "d")]),
            {"encoding": "cp1252"},
        ),
    }
    made = {}
    for name, (lvm, options) in cases.items():
        write_lvm(folder / name, lvm, **options)  # type: ignore[arg-type]
        made[f"read/{name}"] = "written by lvmio (this checkout) for LabVIEW's reader"
    return made

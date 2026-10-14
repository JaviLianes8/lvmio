"""Files written by this checkout of lvmio, for LabVIEW's reader to read back."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lvmio import Channel, LvmFile, Segment, write_lvm


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
            LvmFile([Segment([Channel("Temperatura µ", [21.5, 22.0], unit="°C")])]),
            {"operator": "José", "encoding": "cp1252"},
        ),
        "lvmio_precision.lvm": (LvmFile([Segment([volts, amps])]), {"precision": 9}),
    }
    made = {}
    for name, (lvm, options) in cases.items():
        write_lvm(folder / name, lvm, **options)  # type: ignore[arg-type]
        made[f"read/{name}"] = "written by lvmio (this checkout) for LabVIEW's reader"
    return made

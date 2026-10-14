"""Capture .lvm ground truth from a local LabVIEW 2026 install (Windows only).

LabVIEW writes measurement files through the Write To Measurement File express VI and
its worker VI, and reads files through Read From Measurement File; both are driven over
LabVIEW's ActiveX server. Everything lands in tests/fixtures/labview2026 with a
manifest of sizes and SHA-256 sums. Needs pywin32.

    python scripts/capture_labview.py
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from _cases import COMMENTS, numbers, ties
from _hand_inputs import write_hand_inputs
from _labview_com import LabVIEW, express, read, worker
from _lvmio_inputs import write_inputs

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "labview2026"
BASIC = [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]


def main(argv: list[str]) -> int:
    lv = LabVIEW()
    if argv[:1] == ["--append"]:
        # A second LabVIEW session appending to an existing file repeats the file header.
        worker(lv, Path(argv[1]), [{"rows": [[7.0, 8.0]], "later_session": True}], 1)
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    made: dict[str, str] = {}

    def target(name: str, how: str) -> Path:
        path = OUT / name
        if path.exists():
            path.unlink()
        made[name] = how
        return path

    express(
        lv,
        target(
            "express_default.lvm",
            "Write To Measurement File express VI instance, default configuration",
        ),
        BASIC,
    )
    for code, label in ((0, "no"), (1, "one"), (2, "multi")):
        worker(
            lv,
            target(f"x_columns_{label}.lvm", f"express worker VI, X columns code {code}"),
            [{"rows": BASIC}],
            code,
        )
    worker(
        lv,
        target("numbers.lvm", "express worker VI, seeded values over the double range"),
        [{"rows": numbers()}],
        1,
    )
    inputs = target("numbers_input.json", "the channels given to LabVIEW for numbers.lvm")
    exact = [[value.hex() for value in channel] for channel in numbers()]
    inputs.write_text(json.dumps(exact, indent=1) + "\n", encoding="utf-8")
    specials = [[1.0, math.nan, -0.0], [math.inf, -math.inf, 0.0]]
    worker(
        lv,
        target("specials.lvm", "express worker VI, NaN, infinities and signed zero"),
        [{"rows": specials}],
        1,
    )
    worker(
        lv,
        target(
            "period_decimal.lvm",
            "express worker VI, period chosen as decimal separator on a comma locale",
        ),
        [{"rows": BASIC, "decimal": "."}],
        1,
    )
    passes = [
        {"rows": BASIC, "comment": "first pass"},
        {"rows": [[3.0, 4.0, 5.0]], "comment": "second pass"},
        {"rows": [[6.0], [7.0], [8.0]]},
    ]
    worker(lv, target("segments.lvm", "express worker VI, three appends in one session"), passes, 1)
    appended = target(
        "appended_runs.lvm", "express worker VI, a second session appending to the first file"
    )
    worker(lv, appended, [{"rows": BASIC}], 1)
    subprocess.run([sys.executable, __file__, "--append", str(appended)], check=True)
    worker(
        lv,
        target("comment_cp1252.lvm", "express worker VI, a comment outside ASCII"),
        [{"rows": BASIC, "comment": "caf\u00e9 \u00f1 \u00b5 \u20ac"}],
        1,
    )
    worker(
        lv,
        target("ties.lvm", "express worker VI, exact rounding ties and notation boundaries"),
        [{"rows": ties()}],
        1,
    )
    exact_ties = [[value.hex() for value in channel] for channel in ties()]
    target("ties_input.json", "the channels given to LabVIEW for ties.lvm").write_text(
        json.dumps(exact_ties, indent=1) + "\n", encoding="utf-8"
    )
    passes = [{"rows": [[float(i)]], "comment": text} for i, text in enumerate(COMMENTS)]
    worker(lv, target("comments.lvm", "express worker VI, one data set per comment"), passes, 1)
    target("comments_input.json", "the comments given to LabVIEW for comments.lvm").write_text(
        json.dumps(COMMENTS, indent=1) + "\n", encoding="utf-8"
    )
    for stale in (OUT / "read").glob("*.lvm"):
        stale.unlink()
    made.update(write_hand_inputs(OUT / "read"))
    made.update(write_inputs(OUT / "read"))

    readback: dict[str, Any] = {}
    sources = sorted((OUT / "read").glob("*.lvm"))
    for source in [*sorted(OUT.glob("*.lvm")), *sources]:
        readback[source.relative_to(OUT).as_posix()] = read(lv, source)
    target(
        "read_results.json", "what LabVIEW's Read From Measurement File returns for each .lvm here"
    )
    (OUT / "read_results.json").write_text(json.dumps(readback, indent=1) + "\n", encoding="utf-8")

    manifest = {
        "generated_by": f"LabVIEW {lv.version} (Windows x64) through its ActiveX server",
        "locale_decimal": "comma (Spanish regional settings)",
        "files": {name: _entry(OUT / name, how) for name, how in sorted(made.items())},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return 0


def _entry(path: Path, how: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "how": how}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

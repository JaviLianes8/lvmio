"""LabVIEW's reader follows the Samples count of a segment; lvmio reads the data rows."""

from __future__ import annotations

import json
import math
from pathlib import Path

from lvmio import read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
RESULTS = json.loads((HERE / "read_results.json").read_text(encoding="utf-8"))


def _labview(name: str) -> list[list[float | str]]:
    first = RESULTS[f"read/{name}"][0]
    assert first["error"] == 0
    return list(first["channels"])


def _lvmio(name: str) -> list[float]:
    return read_lvm(HERE / "read" / name).segments[0].channels[0].data


def test_a_samples_count_above_the_rows_pads_in_labview_only() -> None:
    assert _labview("samples_more_than_rows.lvm") == [[1.0, 2.0, "NaN", 0.0, 0.0]]
    assert _lvmio("samples_more_than_rows.lvm") == [1.0, 2.0]


def test_a_samples_count_below_the_rows_cuts_in_labview_only() -> None:
    assert _labview("samples_fewer_than_rows.lvm") == [[1.0]]
    assert _lvmio("samples_fewer_than_rows.lvm") == [1.0, 2.0]


def test_a_blank_samples_count_reads_nothing_in_labview() -> None:
    assert _labview("samples_blank.lvm") == []
    assert _lvmio("samples_blank.lvm") == [1.0, 2.0]


def test_a_missing_samples_line_or_extra_channels_are_refused_by_labview_only() -> None:
    for name in ("samples_missing.lvm", "channels_more_than_columns.lvm"):
        assert RESULTS[f"read/{name}"][0]["error"] == 100
        assert _lvmio(name) == [1.0, 2.0]
    assert not any(math.isnan(v) for v in _lvmio("samples_missing.lvm"))

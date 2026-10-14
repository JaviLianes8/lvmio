"""lvmio against what LabVIEW 2026 wrote and read on the author's machine.

``tests/fixtures/labview2026`` holds files LabVIEW's measurement file writer produced,
hand-written and lvmio-written files given to LabVIEW's reader, and what that reader
returned (``read_results.json``). ``manifest.json`` says how each file was made.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pytest

import lvmio
from lvmio import LvmError, format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
RESULTS: dict[str, list[dict[str, Any]]] = json.loads(
    (HERE / "read_results.json").read_text(encoding="utf-8")
)
WRITTEN = sorted(p.name for p in HERE.glob("*.lvm"))
BASIC = [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]
# LabVIEW reads these by their longest numeric prefix; lvmio refuses them instead.
REFUSED_BY_LVMIO = {"0x10", "1_0", "1,5", "2.5V"}
# LabVIEW's reader truncates its own writer's periods in a file declaring a comma.
READ_DIFFERENTLY = {"period_decimal.lvm"}


def _value(item: float | str) -> float:
    return float(item.replace("Inf", "inf")) if isinstance(item, str) else item


def _same(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) and all(
        (math.isnan(x) and math.isnan(y)) or (x == y and math.copysign(1, x) == math.copysign(1, y))
        for x, y in zip(a, b, strict=True)
    )


@pytest.mark.parametrize("name", sorted(MANIFEST["files"]))
def test_every_capture_matches_its_manifest(name: str) -> None:
    data = (HERE / name).read_bytes()
    entry = MANIFEST["files"][name]
    assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["size"], entry["sha256"])


@pytest.mark.parametrize("name", sorted(n for n in RESULTS if n not in READ_DIFFERENTLY))
def test_lvmio_reads_what_labview_reads(name: str) -> None:
    first = RESULTS[name][0]
    token = _token(name)
    if first["error"]:
        with pytest.raises(LvmError):
            read_lvm(HERE / name)
        return
    if token in REFUSED_BY_LVMIO:
        with pytest.raises(LvmError, match="not a number"):
            read_lvm(HERE / name)
        return
    segment = read_lvm(HERE / name).segments[0]
    width = max((len(c) for c in first["channels"]), default=0)
    ours = [c.data + [math.nan] * (width - len(c.data)) for c in segment]
    theirs = [[_value(v) for v in channel] for channel in first["channels"]]
    assert len(ours) == len(theirs)
    for mine, labview in zip(ours, theirs, strict=True):
        assert _same(mine, labview)


def _token(name: str) -> str | None:
    if not name.startswith("read/token_"):
        return None
    return (HERE / name).read_bytes().decode("utf-8").split("\r\n")[-2].split("\t")[1]


def test_the_refused_spellings_are_exactly_the_ones_labview_reads_in_part() -> None:
    tokens = {_token(n) for n in RESULTS if n.startswith("read/token_")}
    assert tokens >= REFUSED_BY_LVMIO
    for name in RESULTS:
        if _token(name) in REFUSED_BY_LVMIO:
            assert RESULTS[name][0]["error"] == 0


def test_a_period_in_a_comma_file_is_read_as_the_decimal_point() -> None:
    lvm = read_lvm(HERE / "period_decimal.lvm")
    assert lvm.decimal_separator == ","
    assert lvm.segments[0].channels[0].data == BASIC[0]
    assert RESULTS["period_decimal.lvm"][0]["channels"][0] == [1.0, 2.0, -3.0]


@pytest.mark.parametrize(
    "name", [n for n in WRITTEN if n not in ("period_decimal.lvm", "appended_runs.lvm")]
)
def test_rewriting_a_labview_file_gives_back_its_exact_bytes(name: str) -> None:
    raw = (HERE / name).read_bytes().decode("cp1252")
    assert format_lvm(parse_lvm(raw)) == raw


def test_every_x_columns_layout_reads_the_same_channels() -> None:
    for name, layout in [
        ("x_columns_no", "No"),
        ("x_columns_one", "One"),
        ("x_columns_multi", "Multi"),
    ]:
        lvm = read_lvm(HERE / f"{name}.lvm")
        assert lvm.x_columns == layout
        assert [c.name for c in lvm.segments[0]] == ["Untitled", "Untitled 1"]
        assert [c.data for c in lvm.segments[0]] == BASIC
        assert lvm.segments[0].channels[1].time_axis() == [0.0, 1.0, 2.0]


def test_labview_number_format_on_400_seeded_values() -> None:
    inputs = json.loads((HERE / "numbers_input.json").read_text(encoding="utf-8"))
    channels = [
        lvmio.Channel(f"c{i}", [float.fromhex(v) for v in ch]) for i, ch in enumerate(inputs)
    ]
    ours = format_lvm(channels, decimal_separator=",").split("\r\n")
    theirs = (HERE / "numbers.lvm").read_bytes().decode("ascii").split("\r\n")
    start_ours = ours.index(next(line for line in ours if line.startswith("X_Value")))
    start_theirs = theirs.index(next(line for line in theirs if line.startswith("X_Value")))
    rows_ours = [r.split("\t")[1:] for r in ours[start_ours + 1 : -2]]
    rows_theirs = [r.split("\t")[1:] for r in theirs[start_theirs + 1 : -2]]
    assert len(rows_theirs) == 100
    assert rows_ours == rows_theirs


def test_segments_and_their_comments() -> None:
    lvm = read_lvm(HERE / "segments.lvm")
    assert [len(s) for s in lvm] == [2, 1, 3]
    assert [s.comment for s in lvm] == ["first pass", "second pass", ""]
    assert lvm.segments[2].names == ["Untitled", "Untitled 1", "Untitled 2"]
    assert lvm.multi_headings is True


def test_a_second_session_appending_repeats_the_file_header() -> None:
    raw = (HERE / "appended_runs.lvm").read_bytes().decode("ascii")
    assert raw.count("LabVIEW Measurement") == 2
    lvm = parse_lvm(raw)
    assert [len(s) for s in lvm] == [2, 1]
    assert lvm.segments[1].channels[0].data == [7.0, 8.0]


def test_labview_writes_windows_1252_and_lvmio_reads_it() -> None:
    lvm = read_lvm(HERE / "comment_cp1252.lvm")
    assert lvm.segments[0].comment == "caf\u00e9 \u00f1 \u00b5 \u20ac"
    with pytest.raises(LvmError, match="not utf-8 text at byte"):
        read_lvm(HERE / "comment_cp1252.lvm", encoding="utf-8")


def test_specials_and_signed_zero() -> None:
    first, second = read_lvm(HERE / "specials.lvm").segments[0]
    assert math.isnan(first.data[1]) and math.copysign(1, first.data[2]) == -1
    assert second.data == [math.inf, -math.inf, 0.0]


def test_the_express_vi_default_file() -> None:
    lvm = read_lvm(HERE / "express_default.lvm")
    assert (lvm.x_columns, lvm.decimal_separator, lvm.separator) == ("No", ",", "Tab")
    assert [c.data for c in lvm.segments[0]] == BASIC
    assert [c.unit for c in lvm.segments[0]] == ["", ""]

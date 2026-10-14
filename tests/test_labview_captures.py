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

from lvmio import LvmError, format_lvm, parse_lvm, read_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
RESULTS: dict[str, list[dict[str, Any]]] = json.loads(
    (HERE / "read_results.json").read_text(encoding="utf-8")
)
WRITTEN = sorted(p.name for p in HERE.glob("*.lvm"))
BASIC = [[1.0, 2.5, -3.25], [4.0, 5.0, 6.0]]
CRLF, TAB, BACKSLASH = "\r\n", "\t", chr(92)
# LabVIEW reads these cells by their longest numeric prefix (or a blank line as a row);
# lvmio refuses them instead of returning part of the text. GUIDE.md lists them.
LABVIEW_READS_LVMIO_REFUSES = {
    "0x10",
    "1_0",
    "1,5",
    "2.5V",
    "1.5e",
    "1d5",
    "Inf5",
    "NaN1",
    "1E5.5",
    "1.#INF",
    "nan(ind)",
    "0b1",
    "1e5e5",
    "Infinite",
    "infinityx",
    "1 2",
    "read/blank_line_in_rows.lvm",
}
# LabVIEW refuses these (error 100); lvmio reads them. GUIDE.md lists them.
LVMIO_READS_LABVIEW_REFUSES = {"-nan", "+NaN", "   ", "read/no_x_value_column.lvm"}
# LabVIEW's reader truncates its own writer's periods in a file declaring a comma.
READ_DIFFERENTLY = {"period_decimal.lvm"}
# 9999999.9999995 is written by LabVIEW as 10000000,000000, which reads back as 1e7 and is
# then written as 1,000000E+7: the one place a LabVIEW file does not survive a rewrite.
REWRITE_BOUNDARY = {"ties.lvm", "near_ties.lvm", "delta_x_2048hz.lvm", "delta_x_1e-7.lvm"}


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


def _key(name: str) -> str:
    """A token file is known by its cell, any other file by its name."""
    if not name.startswith("read/token_"):
        return name
    lines = [line for line in (HERE / name).read_bytes().decode("utf-8").split(CRLF) if line]
    return lines[-1].split(TAB)[1]


@pytest.mark.parametrize("name", sorted(n for n in RESULTS if n not in READ_DIFFERENTLY))
def test_lvmio_reads_what_labview_reads(name: str) -> None:
    first, key = RESULTS[name][0], _key(name)
    if key in LABVIEW_READS_LVMIO_REFUSES:
        assert first["error"] == 0
        with pytest.raises(LvmError):
            read_lvm(HERE / name)
        return
    if first["error"]:
        assert key in LVMIO_READS_LABVIEW_REFUSES or _refused(name), key
        return
    segment = read_lvm(HERE / name).segments[0]
    width = max((len(c) for c in first["channels"]), default=0)
    ours = [c.data + [math.nan] * (width - len(c.data)) for c in segment]
    theirs = [[_value(v) for v in channel] for channel in first["channels"]]
    assert len(ours) == len(theirs)
    for mine, labview in zip(ours, theirs, strict=True):
        assert _same(mine, labview)
    if name == "read/lvmio_utf8_comment.lvm":
        # LabVIEW decodes the file in its code page, so UTF-8 text comes back garbled.
        written = "caf" + chr(0xE9) + " " + chr(0x20AC)
        assert segment.comment == written
        assert first["comment"] == written.encode("utf-8").decode("cp1252")
        return
    if name == "read/comment_escapes.lvm":
        # LabVIEW turns the malformed codes \zz and a final \4 into NUL; lvmio keeps them.
        assert first["comment"] == "aAb" + TAB + "c" + BACKSLASH + "d" + chr(0)
        assert (
            segment.comment
            == "aAb" + TAB + "c" + BACKSLASH + "d" + BACKSLASH + "zz" + BACKSLASH + "4"
        )
        return
    assert segment.comment == first["comment"]


def _refused(name: str) -> bool:
    try:
        read_lvm(HERE / name)
    except LvmError:
        return True
    return False


def test_the_one_sided_lists_are_all_in_the_captures() -> None:
    keys = {_key(n): n for n in RESULTS}
    for key in LABVIEW_READS_LVMIO_REFUSES | LVMIO_READS_LABVIEW_REFUSES:
        assert key in keys, key
    for key in LVMIO_READS_LABVIEW_REFUSES:
        assert RESULTS[keys[key]][0]["error"] == 100
        read_lvm(HERE / keys[key])


def test_a_period_in_a_comma_file_is_read_as_the_decimal_point() -> None:
    lvm = read_lvm(HERE / "period_decimal.lvm")
    assert lvm.decimal_separator == ","
    assert lvm.segments[0].channels[0].data == BASIC[0]
    assert RESULTS["period_decimal.lvm"][0]["channels"][0] == [1.0, 2.0, -3.0]


@pytest.mark.parametrize(
    "name",
    [n for n in WRITTEN if n not in {"period_decimal.lvm", "appended_runs.lvm", *REWRITE_BOUNDARY}],
)
def test_rewriting_a_labview_file_gives_back_its_exact_bytes(name: str) -> None:
    raw = (HERE / name).read_bytes().decode("cp1252")
    assert format_lvm(parse_lvm(raw)) == raw


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


def test_comments_round_trip_with_labview_escapes() -> None:
    comments = json.loads((HERE / "comments_input.json").read_text(encoding="utf-8"))
    lvm = read_lvm(HERE / "comments.lvm")
    assert [s.comment for s in lvm] == comments
    assert RESULTS["comments.lvm"][0]["comment"] == comments[0]

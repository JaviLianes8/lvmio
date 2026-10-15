"""LabVIEW's number format against every value it wrote in the captures."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import lvmio
from lvmio import format_lvm, parse_lvm

HERE = Path(__file__).parent / "fixtures" / "labview2026"
CRLF, TAB = "\r\n", "\t"


@pytest.mark.parametrize("name", ["numbers", "ties", "exponent_ties"])
def test_labview_number_format_on_every_captured_value(name: str) -> None:
    inputs = json.loads((HERE / f"{name}_input.json").read_text(encoding="utf-8"))
    channels = [
        lvmio.Channel(f"c{i}", [float.fromhex(v) for v in ch]) for i, ch in enumerate(inputs)
    ]
    ours = format_lvm(channels, decimal_separator=",").split("\r\n")
    theirs = (HERE / f"{name}.lvm").read_bytes().decode("ascii").split("\r\n")
    start_ours = ours.index(next(line for line in ours if line.startswith("X_Value")))
    start_theirs = theirs.index(next(line for line in theirs if line.startswith("X_Value")))
    rows_ours = [r.split("\t")[1:] for r in ours[start_ours + 1 : -2]]
    rows_theirs = [r.split("\t")[1:] for r in theirs[start_theirs + 1 : -2]]
    assert len(rows_theirs) * len(inputs) >= 156
    assert rows_ours == rows_theirs


def test_the_rewrite_boundary_is_the_only_difference_in_ties() -> None:
    raw = (HERE / "ties.lvm").read_bytes().decode("ascii")
    again = format_lvm(parse_lvm(raw))
    pairs = zip(raw.split(CRLF), again.split(CRLF), strict=True)
    changed = [(a, b) for a, b in pairs if a != b]
    # The row holding 9999999.9999995 and the row holding its negative, nothing else.
    assert len(changed) == 2
    for before, after in changed:
        assert "10000000,000000" in before and "1,000000E+7" in after
        assert before.replace("10000000,000000", "1,000000E+7") == after


def test_the_largest_values_below_1e_4_also_change_on_a_rewrite() -> None:
    raw = (HERE / "near_ties.lvm").read_bytes().decode("ascii")
    again = format_lvm(parse_lvm(raw))
    pairs = zip(raw.split(CRLF), again.split(CRLF), strict=True)
    changed = [(a, b) for a, b in pairs if a != b]
    assert len(changed) == 1
    before, after = changed[0]
    assert before.replace("1,000000E-4", "0,000100") == after


def test_exact_exponent_ties_follow_labview_at_every_exponent() -> None:
    inputs = json.loads((HERE / "exponent_ties_input.json").read_text(encoding="utf-8"))
    values = [float.fromhex(v) for channel in inputs for v in channel]
    exponents = {math.floor(math.log10(abs(v))) for v in values if v}
    assert exponents == set(range(7, 20))


def _labview_cells(name: str) -> list[tuple[float, str]]:
    inputs = json.loads((HERE / f"{name}_input.json").read_text(encoding="utf-8"))
    channels = [[float.fromhex(v) for v in channel] for channel in inputs]
    lines = (HERE / f"{name}.lvm").read_bytes().decode("ascii").split(CRLF)
    start = next(i for i, line in enumerate(lines) if line.startswith("X_Value"))
    rows = [line.split(TAB)[1:] for line in lines[start + 1 :] if line]
    return [
        (channel[r], row[c]) for r, row in enumerate(rows) for c, channel in enumerate(channels)
    ]


def test_near_ties_differ_from_labview_only_in_the_last_digit() -> None:
    from decimal import Decimal

    from lvmio._number import format_number

    differ = [
        (x, cell) for x, cell in _labview_cells("near_ties") if format_number(x, 6, ",") != cell
    ]
    assert len(differ) == 20
    for value, cell in differ:
        ours = format_number(value, 6, ",")
        mantissa_ours, mantissa_theirs = (
            Decimal(t.split("E")[0].replace(",", ".")) for t in (ours, cell)
        )
        exp_ours, exp_theirs = int(ours.split("E")[1]), int(cell.split("E")[1])
        step = abs(mantissa_ours.scaleb(exp_ours) - mantissa_theirs.scaleb(exp_theirs))
        assert step == Decimal(1).scaleb(exp_ours - 6) or step == Decimal(1).scaleb(exp_ours - 7)
        exact = Decimal(abs(value)).scaleb(-math.floor(math.log10(abs(value)))) * 10**6
        assert abs(exact % 1 - Decimal("0.5")) < Decimal("1e-8")


def test_labview_reads_some_cells_one_unit_in_the_last_place_away() -> None:
    from lvmio import read_lvm

    results = json.loads((HERE / "read_results.json").read_text(encoding="utf-8"))
    theirs = results["read/lvmio_ulp.lvm"][0]["channels"][0]
    ours = read_lvm(HERE / "read" / "lvmio_ulp.lvm").segments[0].channels[0].data
    assert len(ours) == len(theirs) == 6
    for mine, labview in zip(ours, theirs, strict=True):
        assert labview != mine
        assert abs(labview - mine) == math.ulp(mine)

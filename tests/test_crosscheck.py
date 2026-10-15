"""Interoperability: parse the same .lvm file with lvmio and with the
independent ``lvm_read`` package, and assert the numeric data agrees element for
element. This checks lvmio against an independent reader, not just against a spec
reading.
"""

import math
from pathlib import Path

import pytest

from lvmio import read_lvm

lvm_read = pytest.importorskip("lvm_read")
np = pytest.importorskip("numpy")

FIXTURES = Path(__file__).parent / "fixtures"

FILES = [
    "short.lvm",
    "comma_separator.lvm",
    "comments_on_some_rows.lvm",
    "with_empty_fields.lvm",
]


def _same(a: float, b: float) -> bool:
    return (math.isnan(a) and math.isnan(b)) or abs(a - b) < 1e-9


@pytest.mark.parametrize("name", FILES)
def test_numeric_data_matches_lvm_read(name: str) -> None:
    path = FIXTURES / name
    ours = read_lvm(path)
    oracle = lvm_read.read(str(path), read_from_pickle=False, dump_file=False)

    segment = ours.segments[0]
    oracle_segment = oracle[0]
    oracle_names = list(oracle_segment["Channel names"])
    oracle_data = np.asarray(oracle_segment["data"])

    assert segment.names, "expected at least one channel"
    for channel in segment.channels:
        column = oracle_data[:, oracle_names.index(channel.name)].tolist()
        # Later data sets (rows with a comment) are further segments in lvmio.
        mine_all = [
            v for seg in ours.segments if seg.names == segment.names for v in seg[channel.name].data
        ]
        # lvm_read pads every channel to the rows; lvmio, like LabVIEW, stops at Samples.
        assert all(math.isnan(v) for v in column[len(mine_all) :])
        for mine, theirs in zip(mine_all, column[: len(mine_all)], strict=True):
            assert _same(float(mine), float(theirs))


def test_oracle_and_lvmio_agree_on_channel_count() -> None:
    path = FIXTURES / "comma_separator.lvm"
    ours = read_lvm(path)
    oracle = lvm_read.read(str(path), read_from_pickle=False, dump_file=False)
    assert len(ours.segments[0]) == oracle[0]["Channels"]


LABVIEW = FIXTURES / "labview2026"
CAPTURES = [
    "express_default.lvm",
    "x_columns_no.lvm",
    "x_columns_one.lvm",
    "x_columns_multi.lvm",
    "numbers.lvm",
    "ties.lvm",
    "specials.lvm",
    "comment_cp1252.lvm",
    "read/lvmio_one.lvm",
    "read/lvmio_multi.lvm",
    "read/lvmio_decimal_comma.lvm",
    "read/lvmio_comma.lvm",
]


@pytest.mark.parametrize("name", CAPTURES)
def test_labview_captures_match_lvm_read_exactly(name: str) -> None:
    path = LABVIEW / name
    segment = read_lvm(path).segments[0]
    oracle = lvm_read.read(str(path), read_from_pickle=False, dump_file=False)[0]
    names = list(oracle["Channel names"])
    data = np.asarray(oracle["data"])
    for channel in segment.channels:
        column = [float(v) for v in data[:, names.index(channel.name)].tolist()]
        assert all(math.isnan(v) for v in column[len(channel.data) :])
        for mine, theirs in zip(channel.data, column[: len(channel.data)], strict=True):
            assert (math.isnan(mine) and math.isnan(theirs)) or mine == theirs

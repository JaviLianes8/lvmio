"""Real interoperability: parse the same genuine .lvm file with lvmio and with the
independent ``lvm_read`` package, and assert the numeric data agrees element for
element. This proves lvmio reads what real LabVIEW tools read, not just what a spec
reading suggests.
"""

import math
from pathlib import Path

import pytest

from lvmio import read_lvm

lvm_read = pytest.importorskip("lvm_read")
np = pytest.importorskip("numpy")

FIXTURES = Path(__file__).parent / "fixtures"

REAL_FILES = [
    "short.lvm",
    "comma_separator.lvm",
    "comments_on_some_rows.lvm",
    "with_empty_fields.lvm",
]


def _same(a: float, b: float) -> bool:
    return (math.isnan(a) and math.isnan(b)) or abs(a - b) < 1e-9


@pytest.mark.parametrize("name", REAL_FILES)
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
        assert len(channel.data) == len(column)
        for mine, theirs in zip(channel.data, column, strict=True):
            assert _same(float(mine), float(theirs))


def test_oracle_and_lvmio_agree_on_channel_count() -> None:
    path = FIXTURES / "comma_separator.lvm"
    ours = read_lvm(path)
    oracle = lvm_read.read(str(path), read_from_pickle=False, dump_file=False)
    assert len(ours.segments[0]) == oracle[0]["Channels"]

"""Hostile, huge and malformed input: only LvmError, short messages, linear time."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from lvmio import LvmError, format_lvm, parse_lvm, read_lvm

LABVIEW = Path(__file__).parent / "fixtures" / "labview2026"
SEEDS = [p.read_bytes().decode("cp1252") for p in sorted(LABVIEW.glob("*.lvm"))]
PIECES = [
    "\t",
    ",",
    "\r\n",
    "\n",
    "\r",
    "X_Value",
    "Comment",
    "Channels",
    "***End_of_Header***",
    "LabVIEW Measurement",
    "Separator\tComma",
    "Decimal_Separator\t,",
    "X_Columns\tMulti",
    "NaN",
    "-Inf",
    "1e309",
    "",
    " ",
    "\ufeff",
    "\x00",
    "\u2028",
    "1_0",
    "9" * 50,
]


def _mutate(rng: random.Random, text: str) -> str:
    lines = text.split("\r\n")
    for _ in range(rng.randint(1, 6)):
        kind = rng.randrange(5)
        i = rng.randrange(len(lines))
        if kind == 0:
            del lines[i]
        elif kind == 1:
            lines.insert(i, lines[rng.randrange(len(lines))])
        elif kind == 2:
            cut = rng.randrange(len(lines[i]) + 1)
            lines[i] = lines[i][:cut] + rng.choice(PIECES) + lines[i][cut:]
        elif kind == 3:
            lines[i] = lines[i][: rng.randrange(len(lines[i]) + 1)]
        else:
            lines[i:i] = rng.choice(SEEDS).split("\r\n")[: rng.randint(1, 30)]
    return "\r\n".join(lines)


def test_seeded_mutations_raise_only_lvm_error() -> None:
    rng = random.Random(1234)
    parsed = refused = 0
    for _ in range(3000):
        text = _mutate(rng, rng.choice(SEEDS))
        try:
            lvm = parse_lvm(text)
        except LvmError as exc:
            refused += 1
            assert len(str(exc)) < 200
            continue
        parsed += 1
        for segment in lvm:
            for channel in segment:
                assert len(channel.data) == len(segment.channels[0].data)
    assert parsed > 500 and refused > 100


def test_random_text_raises_only_lvm_error() -> None:
    rng = random.Random(99)
    for _ in range(3000):
        body = "".join(rng.choice(PIECES) for _ in range(rng.randint(0, 40)))
        try:
            parse_lvm("LabVIEW Measurement\t\r\n" + body)
        except LvmError as exc:
            assert len(str(exc)) < 200


def test_parsed_mutations_can_be_written_back_or_are_refused_cleanly() -> None:
    rng = random.Random(5)
    for _ in range(800):
        try:
            lvm = parse_lvm(_mutate(rng, rng.choice(SEEDS)))
        except LvmError:
            continue
        try:
            again = parse_lvm(format_lvm(lvm))
        except (TypeError, ValueError):
            continue
        assert [s.names for s in again] == [s.names for s in lvm]


TRUNCATED = [
    "",
    "\n" * 1000,
    "x" * 100_000,
    "LabVIEW Measurement",
    "LabVIEW Measurement\t\nSeparator\tTab\n",
    "LabVIEW Measurement\t\n***End_of_Header***\t\nChannels\t1\n",
    "LabVIEW Measurement\t\n***End_of_Header***\t\nChannels\t1\n***End_of_Header***\t\n",
    "LabVIEW Measurement\t\n***End_of_Header***\t\n" + "Channels\t1\n" * 50_000,
]


@pytest.mark.parametrize("index", range(len(TRUNCATED)))
def test_truncated_and_empty_files_are_refused(index: int) -> None:
    with pytest.raises(LvmError) as info:
        parse_lvm(TRUNCATED[index])
    assert len(str(info.value)) < 200


def test_wrong_types_and_paths() -> None:
    with pytest.raises(TypeError):
        parse_lvm(b"LabVIEW Measurement")  # type: ignore[arg-type]
    with pytest.raises(OSError):
        read_lvm(LABVIEW)
    with pytest.raises(LookupError):
        read_lvm(LABVIEW / "specials.lvm", encoding="no-such-codec")


def _file(rows: int, columns: int, cell: str = "1.5") -> str:
    head = "LabVIEW Measurement\t\r\n***End_of_Header***\t\r\n\t\r\n"
    names = "\t".join(f"c{i}" for i in range(columns))
    seg = f"Channels\t{columns}\r\n***End_of_Header***\t\r\nX_Value\t{names}\tComment\r\n"
    row = "\t" + "\t".join([cell] * columns) + "\r\n"
    return head + seg + row * rows


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize(
    "build",
    [
        lambda n: _file(n, 2),
        lambda n: _file(2, n),
        lambda n: _file(2, 1, "1" * n),
        lambda n: (
            "LabVIEW Measurement\t\r\n" + "Operator\t" + "y" * n + "\r\n***End_of_Header***\t\r\n"
        ),
    ],
)
def test_time_grows_linearly(build: Callable[[int], str]) -> None:
    small, large = build(20_000), build(80_000)
    ratio = _seconds(lambda: parse_lvm(large)) / max(_seconds(lambda: parse_lvm(small)), 1e-4)
    assert ratio < 10


def test_writer_time_grows_linearly() -> None:
    def write(n: int) -> Callable[[], object]:
        return lambda: format_lvm({"a": [1.5] * n, "b": [2.5] * n}, x_columns="Multi")

    ratio = _seconds(write(80_000)) / max(_seconds(write(20_000)), 1e-4)
    assert ratio < 10

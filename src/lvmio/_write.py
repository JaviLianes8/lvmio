"""Serialise typed objects to LabVIEW Measurement (.lvm) text, as LabVIEW writes it."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from operator import index as as_index
from typing import SupportsFloat

from ._check import as_file, canonical, check_file
from ._model import Channel, LvmFile, Segment
from ._number import shorten
from ._read import encoding_name
from ._render import render


def format_lvm(
    data: LvmFile | Segment | Sequence[Channel] | Mapping[str, Iterable[SupportsFloat]],
    *,
    operator: str | None = None,
    date: str | None = None,
    time: str | None = None,
    decimal_separator: str | None = None,
    separator: str | None = None,
    x_columns: str | None = None,
    precision: int = 6,
) -> str:
    """Return ``data`` as LabVIEW Measurement text, with CRLF line endings.

    ``data`` may be a full ``LvmFile``, a single ``Segment``, a sequence of ``Channel``
    objects, or a mapping of channel name to samples. Samples may be any iterable of real
    numbers (a list, a NumPy array, a generator); ``bool`` and text are refused. Keyword
    arguments override the matching file header fields: ``separator`` is ``"Tab"`` or ``"Comma"``,
    ``decimal_separator`` is ``"."`` or ``","``, ``x_columns`` is ``"No"``, ``"One"`` or
    ``"Multi"``. Samples use ``precision`` decimals in LabVIEW's number format.

    >>> text = format_lvm({"V": [1.5, 1e-9]}, operator="lab", date="2026/10/14")
    >>> text.splitlines()[-3:-1]
    ['0.000000\\t1.500000', '1.000000\\t1.000000E-9']

    Raises ``TypeError`` for data of the wrong type and ``ValueError`` for values that
    cannot be written (a name holding the separator, an unknown separator, ...); the
    guide lists every case.
    """
    lvm = as_file(data)
    lvm = replace(
        lvm,
        operator=lvm.operator if operator is None else operator,
        date=lvm.date if date is None else date,
        time=lvm.time if time is None else time,
        decimal_separator=lvm.decimal_separator if decimal_separator is None else decimal_separator,
        separator=lvm.separator if separator is None else separator,
        x_columns=lvm.x_columns if x_columns is None else x_columns,
    )
    if isinstance(precision, bool) or not hasattr(type(precision), "__index__"):
        raise TypeError(f"precision must be an int, not {type(precision).__name__}")
    precision = int.__index__(as_index(precision))
    if not 0 <= precision <= 17:
        raise ValueError("precision must be between 0 and 17")
    lvm = check_file(canonical(lvm))
    return "\r\n".join(render(lvm, precision)) + "\r\n"


def write_lvm(
    path: str | os.PathLike[str],
    data: LvmFile | Segment | Sequence[Channel] | Mapping[str, Iterable[SupportsFloat]],
    *,
    operator: str | None = None,
    date: str | None = None,
    time: str | None = None,
    decimal_separator: str | None = None,
    separator: str | None = None,
    x_columns: str | None = None,
    precision: int = 6,
    encoding: str = "utf-8",
) -> None:
    """Write ``data`` to ``path`` as a LabVIEW Measurement file.

    Takes the same arguments as ``format_lvm``. ``encoding`` defaults to UTF-8; pass
    ``"cp1252"`` to match what LabVIEW writes on a Western-European Windows system.
    Nothing is written when the data is refused. Raises what ``format_lvm`` raises,
    ``ValueError`` for text the encoding cannot hold, ``LookupError`` for an unknown
    encoding and ``OSError`` when the file cannot be written.

    >>> import lvmio, pathlib, tempfile
    >>> path = pathlib.Path(tempfile.mkdtemp(), "run.lvm")
    >>> write_lvm(path, [Channel("V", [1.0, 2.0], unit="V")], decimal_separator=",")
    >>> lvmio.read_lvm(path).segments[0]["V"].data
    [1.0, 2.0]
    """
    text = format_lvm(
        data,
        operator=operator,
        date=date,
        time=time,
        decimal_separator=decimal_separator,
        separator=separator,
        x_columns=x_columns,
        precision=precision,
    )
    name = encoding_name(encoding)
    try:
        payload = text.encode(encoding)
    except UnicodeError as exc:
        start = exc.start if isinstance(exc, UnicodeEncodeError) else 0
        character = shorten(text[start : start + 1])
        raise ValueError(f"the character {character} cannot be written as {name}") from None
    with open(os.fspath(path), "wb") as handle:
        handle.write(payload)

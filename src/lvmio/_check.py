"""Check and normalise what the writer is given, before anything is written."""

from __future__ import annotations

import numbers
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal

from ._model import Channel, LvmFile, Segment
from ._number import shorten

_SEPARATORS = {"tab": "Tab", "comma": "Comma"}
_X_COLUMNS = {"no": "No", "one": "One", "multi": "Multi"}
_RESERVED = {"x_value", "comment"}


def as_file(data: object) -> LvmFile:
    """Wrap any accepted input in an ``LvmFile``."""
    if isinstance(data, LvmFile):
        return data
    if isinstance(data, Segment):
        return LvmFile(segments=[data])
    if isinstance(data, Mapping):
        channels = []
        for name, values in data.items():
            if not isinstance(name, str):
                raise TypeError(f"channel names must be str, not {type(name).__name__}")
            channels.append(Channel(name, _samples(values, name)))
        return LvmFile(segments=[Segment(channels)])
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        items = list(data)
        for item in items:
            if not isinstance(item, Channel):
                raise TypeError(f"expected Channel objects, got {type(item).__name__}")
        return LvmFile(segments=[Segment(items)])
    raise TypeError(f"cannot write {type(data).__name__} as a measurement file")


def canonical(lvm: LvmFile) -> LvmFile:
    """Check the layout fields and spell them the way LabVIEW does."""
    separator = _choice(lvm.separator, _SEPARATORS, "separator")
    x_columns = _choice(lvm.x_columns, _X_COLUMNS, "x_columns")
    if lvm.decimal_separator not in (".", ","):
        raise ValueError(
            f"decimal_separator must be '.' or ',', not {_text(lvm.decimal_separator)}"
        )
    if separator == "Comma" and lvm.decimal_separator == ",":
        raise ValueError("a comma cannot be both the separator and the decimal separator")
    return replace(lvm, separator=separator, x_columns=x_columns)


def check_file(lvm: LvmFile) -> LvmFile:
    """Refuse text that would change the file's layout; return numbers as floats."""
    delim = "," if lvm.separator == "Comma" else "\t"
    for name in ("writer_version", "reader_version", "time_pref", "operator", "date", "time"):
        _field(getattr(lvm, name), name, delim)
    if not isinstance(lvm.multi_headings, bool):
        raise TypeError(f"multi_headings must be bool, not {type(lvm.multi_headings).__name__}")
    if not isinstance(lvm.segments, (list, tuple)):
        raise TypeError(f"segments must be a list, not {type(lvm.segments).__name__}")
    segments = []
    for segment in lvm.segments:
        if not isinstance(segment, Segment):
            raise TypeError(f"expected Segment objects, got {type(segment).__name__}")
        segments.append(_segment(segment, delim))
    return replace(lvm, segments=segments)


def _segment(seg: Segment, delim: str) -> Segment:
    _field(seg.date, "segment date", delim)
    _field(seg.time, "segment time", delim)
    if not isinstance(seg.comment, str):
        raise TypeError(f"comment must be str, not {type(seg.comment).__name__}")
    if "\r" in seg.comment or "\n" in seg.comment:
        raise ValueError(f"comment cannot hold a line break: {shorten(seg.comment)}")
    if not isinstance(seg.channels, (list, tuple)):
        raise TypeError(f"channels must be a list, not {type(seg.channels).__name__}")
    channels = []
    for channel in seg.channels:
        if not isinstance(channel, Channel):
            raise TypeError(f"expected Channel objects, got {type(channel).__name__}")
        _field(channel.name, "channel name", delim)
        if not channel.name or channel.name.lower() in _RESERVED:
            raise ValueError(f"channel name {_text(channel.name)} is reserved or empty")
        _field(channel.unit, "unit", delim)
        _field(channel.x_dimension, "x_dimension", delim)
        if not channel.x_dimension:
            raise ValueError("x_dimension cannot be empty")
        channels.append(
            replace(
                channel,
                data=_samples(channel.data, channel.name),
                x0=_number(channel.x0, "x0"),
                delta_x=_number(channel.delta_x, "delta_x"),
            )
        )
    return replace(seg, channels=channels)


def _samples(values: object, name: str) -> list[float]:
    """Any iterable of real numbers: a list, a tuple, a NumPy array, a generator."""
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Iterable):
        raise TypeError(f"samples of {_text(name)} must be an iterable of numbers")
    return [_number(v, f"a sample of {_text(name)}") for v in values]


def _number(value: object, what: str) -> float:
    """A real number (``int``, ``float``, ``Fraction``, ``Decimal``, NumPy) as a double."""
    if isinstance(value, bool) or not isinstance(value, (numbers.Real, Decimal)):
        raise TypeError(f"{what} must be a real number, not {type(value).__name__}")
    try:
        return float(value)
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"{what} cannot be held in a double: {type(exc).__name__}") from None


def _field(value: object, name: str, delim: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, not {type(value).__name__}")
    if delim in value or "\r" in value or "\n" in value:
        raise ValueError(f"{name} cannot hold the separator or a line break: {shorten(value)}")
    if value != value.strip(" \t"):
        raise ValueError(f"{name} cannot start or end with blanks: {shorten(value)}")


def _choice(value: object, options: dict[str, str], name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, not {type(value).__name__}")
    if value.lower() not in options:
        raise ValueError(f"{name} must be one of {', '.join(options.values())}: {_text(value)}")
    return options[value.lower()]


def _text(value: object) -> str:
    return shorten(value) if isinstance(value, str) else type(value).__name__

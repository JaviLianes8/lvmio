"""Check and normalise what the writer is given, before anything is written."""

from __future__ import annotations

import math
import numbers
from collections.abc import Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
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
    decimal = _exact(lvm.decimal_separator, "decimal_separator")
    if decimal not in (".", ","):
        raise ValueError(f"decimal_separator must be '.' or ',', not {shorten(decimal)}")
    if separator == "Comma" and decimal == ",":
        raise ValueError("a comma cannot be both the separator and the decimal separator")
    return replace(lvm, separator=separator, x_columns=x_columns, decimal_separator=decimal)


def check_file(lvm: LvmFile) -> LvmFile:
    """Refuse text that would read back differently; return exact str, list and float copies."""
    delim = "," if lvm.separator == "Comma" else "\t"
    names = ("writer_version", "reader_version", "time_pref", "operator", "date", "time")
    text = {name: _field(getattr(lvm, name), name, delim) for name in names}
    if not isinstance(lvm.multi_headings, bool):
        raise TypeError(f"multi_headings must be bool, not {type(lvm.multi_headings).__name__}")
    if not isinstance(lvm.segments, (list, tuple)):
        raise TypeError(f"segments must be a list, not {type(lvm.segments).__name__}")
    segments = []
    for segment in lvm.segments:
        if not isinstance(segment, Segment):
            raise TypeError(f"expected Segment objects, got {type(segment).__name__}")
        segments.append(_segment(segment, delim))
    return replace(
        lvm,
        segments=segments,
        writer_version=text["writer_version"],
        reader_version=text["reader_version"],
        time_pref=text["time_pref"],
        operator=text["operator"],
        date=text["date"],
        time=text["time"],
        description=_description(lvm.description),
    )


def _segment(seg: Segment, delim: str) -> Segment:
    date = _field(seg.date, "segment date", delim)
    time = _field(seg.time, "segment time", delim)
    comment = _exact(seg.comment, "comment")
    if not isinstance(seg.channels, (list, tuple)):
        raise TypeError(f"channels must be a list, not {type(seg.channels).__name__}")
    channels = []
    for channel in seg.channels:
        if not isinstance(channel, Channel):
            raise TypeError(f"expected Channel objects, got {type(channel).__name__}")
        name = _field(channel.name, "channel name", delim)
        if not name or name.lower() in _RESERVED:
            raise ValueError(f"channel name {shorten(name)} is reserved or empty")
        x_dimension = _field(channel.x_dimension, "x_dimension", delim)
        x0 = _finite(channel.x0, "x0")
        channels.append(
            Channel(
                name=name,
                data=_samples(channel.data, name),
                unit=_field(channel.unit, "unit", delim),
                x0=x0,
                delta_x=_finite(channel.delta_x, "delta_x"),
                x_dimension=x_dimension,
                date=_field(channel.date, "channel date", delim),
                time=_field(channel.time, "channel time", delim),
            )
        )
    if comment and not any(c.data for c in channels):
        raise ValueError("a comment needs at least one data row to be written in")
    if (date or time) and not channels:
        raise ValueError("a segment date or time needs at least one channel to be written in")
    notes = _field(seg.notes, "notes", delim)
    return Segment(channels, date=date, time=time, comment=comment, notes=notes)


def _samples(values: object, name: str) -> list[float]:
    """Any ordered iterable of real numbers: a list, a tuple, a NumPy array, a generator."""
    unordered = (str, bytes, bytearray, memoryview, AbstractSet, Mapping)
    if isinstance(values, unordered) or not isinstance(values, Iterable):
        raise TypeError(f"samples of {shorten(name)} must be an ordered iterable of numbers")
    return [_number(v, f"a sample of {shorten(name)}") for v in values]


def _finite(value: object, what: str) -> float:
    number = _number(value, what)
    if not math.isfinite(number):
        raise ValueError(f"{what} must be finite, not {number}")
    return number


def _number(value: object, what: str) -> float:
    """A real number (``int``, ``float``, ``Fraction``, ``Decimal``, NumPy) as a double."""
    if isinstance(value, bool) or not isinstance(value, (numbers.Real, Decimal)):
        raise TypeError(f"{what} must be a real number, not {type(value).__name__}")
    try:
        result = float(value)
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"{what} cannot be held in a double: {type(exc).__name__}") from None
    if math.isinf(result) and isinstance(value, Decimal) and value.is_finite():
        raise ValueError(f"{what} cannot be held in a double: too large")
    return result


def _description(value: object) -> str:
    """Any text, escaped when written; blanks at either end would be lost on reading."""
    text = _exact(value, "description")
    if text != text.strip():
        raise ValueError(f"description cannot start or end with blanks: {shorten(text)}")
    return text


def _exact(value: object, name: str) -> str:
    """An exact ``str`` copy, so a subclass cannot change what is checked or written."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str, not {type(value).__name__}")
    return str.__str__(value)


def _field(value: object, name: str, delim: str) -> str:
    text = _exact(value, name)
    if delim in text or "\r" in text or "\n" in text:
        raise ValueError(f"{name} cannot hold the separator or a line break: {shorten(text)}")
    if text != text.strip():
        raise ValueError(f"{name} cannot start or end with blanks: {shorten(text)}")
    return text


def _choice(value: object, options: dict[str, str], name: str) -> str:
    text = _exact(value, name)
    if text.lower() not in options:
        raise ValueError(f"{name} must be one of {', '.join(options.values())}: {shorten(text)}")
    return options[text.lower()]

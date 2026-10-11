"""Typed representation of a LabVIEW Measurement (.lvm) file."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Channel:
    """One measured signal: its name, samples and X axis parameters."""

    name: str
    data: list[float]
    unit: str = ""
    x0: float = 0.0
    delta_x: float = 1.0
    x_dimension: str = "Time"


@dataclass
class Segment:
    """A block of channels sharing one header, as LabVIEW writes per packet."""

    channels: list[Channel]
    date: str = ""
    time: str = ""

    @property
    def samples(self) -> list[int]:
        """The sample count of each channel, in order."""
        return [len(c.data) for c in self.channels]


@dataclass
class LvmFile:
    """A whole .lvm file: the file header fields and one or more segments."""

    segments: list[Segment] = field(default_factory=list)
    writer_version: str = "2"
    reader_version: str = "2"
    separator: str = "Tab"
    decimal_separator: str = "."
    x_columns: str = "One"
    time_pref: str = "Relative"
    operator: str = "unknown"
    date: str = ""
    time: str = ""

    @property
    def multi_headings(self) -> bool:
        """Whether the file carries a header per segment (more than one segment)."""
        return len(self.segments) > 1

"""Typed representation of a LabVIEW Measurement (.lvm) file."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Channel:
    """One measured signal: its name, samples and X axis parameters."""

    name: str
    data: list[float]
    unit: str = ""
    x0: float = 0.0
    delta_x: float = 1.0
    x_dimension: str = "Time"

    def __len__(self) -> int:
        """The number of samples in the channel."""
        return len(self.data)

    def __iter__(self) -> Iterator[float]:
        """Iterate over the channel samples in order."""
        return iter(self.data)

    def time_axis(self) -> list[float]:
        """The X axis values, one per sample, as ``x0 + i * delta_x``."""
        return [self.x0 + i * self.delta_x for i in range(len(self.data))]


@dataclass(frozen=True)
class Segment:
    """A block of channels sharing one header, as LabVIEW writes per packet."""

    channels: list[Channel]
    date: str = ""
    time: str = ""

    @property
    def samples(self) -> list[int]:
        """The sample count of each channel, in order."""
        return [len(c.data) for c in self.channels]

    @property
    def names(self) -> list[str]:
        """The channel names, in order."""
        return [c.name for c in self.channels]

    def get(self, name: str) -> Channel | None:
        """Return the first channel called ``name``, or ``None`` if absent."""
        for channel in self.channels:
            if channel.name == name:
                return channel
        return None

    def __getitem__(self, name: str) -> Channel:
        """Return the first channel called ``name`` or raise ``KeyError``."""
        channel = self.get(name)
        if channel is None:
            raise KeyError(name)
        return channel

    def __contains__(self, name: object) -> bool:
        """Whether a channel with this name exists in the segment."""
        return isinstance(name, str) and self.get(name) is not None

    def __len__(self) -> int:
        """The number of channels in the segment."""
        return len(self.channels)

    def __iter__(self) -> Iterator[Channel]:
        """Iterate over the channels in order."""
        return iter(self.channels)


@dataclass(frozen=True)
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

    def __len__(self) -> int:
        """The number of data segments in the file."""
        return len(self.segments)

    def __iter__(self) -> Iterator[Segment]:
        """Iterate over the data segments in order."""
        return iter(self.segments)

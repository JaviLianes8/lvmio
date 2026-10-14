"""Typed representation of a LabVIEW Measurement (.lvm) file."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Channel:
    """One measured signal: its name, samples and X axis parameters.

    ``date`` and ``time`` are the channel's own cells of the segment's ``Date`` and
    ``Time`` lines; the writer uses the segment's values for a channel that leaves them
    empty.

    >>> ch = Channel("Voltage", [1.0, 2.0, 3.0], unit="V", x0=0.5, delta_x=0.25)
    >>> len(ch), list(ch), ch.time_axis()
    (3, [1.0, 2.0, 3.0], [0.5, 0.75, 1.0])
    """

    name: str
    data: list[float]
    unit: str = ""
    x0: float = 0.0
    delta_x: float = 1.0
    x_dimension: str = "Time"
    date: str = ""
    time: str = ""

    def __len__(self) -> int:
        """The number of samples in the channel."""
        return len(self.data)

    def __iter__(self) -> Iterator[float]:
        """Iterate over the channel samples in order."""
        return iter(self.data)

    def time_axis(self) -> list[float]:
        """The X axis values, one per sample, as ``x0 + i * delta_x``.

        >>> Channel("t", [0.0, 0.0], x0=1.0, delta_x=0.5).time_axis()
        [1.0, 1.5]
        """
        return [self.x0 + i * self.delta_x for i in range(len(self.data))]


@dataclass(frozen=True)
class Segment:
    """A block of channels sharing one header, as LabVIEW writes per data set.

    ``comment`` is the text in the Comment column of the first data row, which is
    where LabVIEW puts the comment of each data set. ``notes`` is the segment header's
    ``Notes`` line, which LabVIEW writes when the channels' X values differ.

    >>> seg = Segment([Channel("V", [1.0]), Channel("I", [2.0])], comment="run 1")
    >>> seg.names, seg.samples, seg["I"].data, "V" in seg, seg.get("X")
    (['V', 'I'], [1, 1], [2.0], True, None)
    """

    channels: list[Channel]
    date: str = ""
    time: str = ""
    comment: str = ""
    notes: str = ""

    @property
    def samples(self) -> list[int]:
        """The sample count of each channel, in order."""
        return [len(c.data) for c in self.channels]

    @property
    def names(self) -> list[str]:
        """The channel names, in order."""
        return [c.name for c in self.channels]

    def get(self, name: str) -> Channel | None:
        """Return the first channel called ``name``, or ``None`` if absent.

        >>> Segment([Channel("V", [1.0])]).get("V").name
        'V'
        """
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
    """A whole .lvm file: the file header fields and one or more segments.

    ``multi_headings`` is the file's ``Multi_Headings`` field; the writer sets it to
    ``Yes`` whenever the file has more than one segment. ``description`` is the file
    header's ``Description`` line (LabVIEW's File Description), escaped like a comment.

    >>> lvm = LvmFile([Segment([Channel("V", [1.0])])], operator="lab")
    >>> len(lvm), lvm.operator, lvm.x_columns, [len(s) for s in lvm]
    (1, 'lab', 'One', [1])
    """

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
    multi_headings: bool = False
    description: str = ""

    def __len__(self) -> int:
        """The number of data segments in the file."""
        return len(self.segments)

    def __iter__(self) -> Iterator[Segment]:
        """Iterate over the data segments in order."""
        return iter(self.segments)

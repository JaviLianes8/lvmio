"""Typed reader and writer for the LabVIEW Measurement (.lvm) file format.

>>> import lvmio
>>> lvm = lvmio.parse_lvm(lvmio.format_lvm({"V": [1.0, 2.5]}))
>>> lvm.segments[0]["V"].data
[1.0, 2.5]
"""

from __future__ import annotations

from ._errors import LvmError
from ._model import Channel, LvmFile, Segment
from ._read import parse_lvm, read_lvm
from ._write import format_lvm, write_lvm

__version__ = "1.0.0"

__all__ = [
    "Channel",
    "LvmError",
    "LvmFile",
    "Segment",
    "format_lvm",
    "parse_lvm",
    "read_lvm",
    "write_lvm",
]

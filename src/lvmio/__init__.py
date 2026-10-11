"""Typed reader and writer for the LabVIEW Measurement (.lvm) file format."""

from __future__ import annotations

from ._errors import LvmError
from ._model import Channel, LvmFile, Segment
from ._read import parse_lvm, read_lvm
from ._write import write_lvm

__version__ = "0.2.0"

__all__ = [
    "Channel",
    "LvmError",
    "LvmFile",
    "Segment",
    "parse_lvm",
    "read_lvm",
    "write_lvm",
]

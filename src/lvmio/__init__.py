"""Typed reader and writer for the LabVIEW Measurement (.lvm) file format."""

from __future__ import annotations

from ._errors import LvmError
from ._model import Channel, LvmFile, Segment
from ._read import read_lvm
from ._write import write_lvm

__version__ = "0.1.0"

__all__ = [
    "Channel",
    "LvmError",
    "LvmFile",
    "Segment",
    "read_lvm",
    "write_lvm",
]

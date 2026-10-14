"""Error types for the lvmio package."""

from __future__ import annotations


class LvmError(ValueError):
    """Raised when text is not a valid LabVIEW Measurement file.

    The message says where (a line number when there is one) and quotes at most a
    short piece of the offending text.

    >>> import lvmio
    >>> lvmio.parse_lvm("hello")
    Traceback (most recent call last):
    ...
    lvmio._errors.LvmError: not a LabVIEW Measurement file: line 1 is 'hello'
    """

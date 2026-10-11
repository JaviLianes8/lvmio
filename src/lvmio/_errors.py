"""Error types for the lvmio package."""

from __future__ import annotations


class LvmError(ValueError):
    """Raised when text is not a valid LabVIEW Measurement file."""

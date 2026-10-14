"""Comment cells: the escapes LabVIEW's measurement file writer and reader use."""

from __future__ import annotations

import re

_CODE = re.compile(r"\\(\\|[0-9A-Fa-f]{2})")


def escape_comment(text: str, delim: str) -> str:
    """Escape a comment as LabVIEW does: control characters as ``\\XX``, ``\\`` doubled.

    In a comma-separated file a comma is escaped too, so the comment stays one cell.

    >>> escape_comment("a\\tb\\\\c", "\\t")
    'a\\\\09b\\\\\\\\c'
    >>> escape_comment("x,y", ",")
    'x\\\\2Cy'
    """
    out = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif ord(char) < 0x20 or (char == "," and delim == ","):
            out.append(f"\\{ord(char):02X}")
        else:
            out.append(char)
    return "".join(out)


def unescape_comment(text: str) -> str:
    """Decode ``\\\\`` and ``\\XX``; any other backslash is kept as written.

    >>> unescape_comment("line1\\\\0D\\\\0Aline2 C:\\\\\\\\data \\\\zz")
    'line1\\r\\nline2 C:\\\\data \\\\zz'
    """
    return _CODE.sub(lambda m: "\\" if m.group(1) == "\\" else chr(int(m.group(1), 16)), text)

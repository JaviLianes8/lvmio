"""Command line interface for lvmio: inspect and export .lvm files."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from . import __version__
from ._cli_output import dispatch
from ._model import LvmFile
from ._number import shorten
from ._read import decode, parse_lvm, read_lvm

_EPILOG = """examples:
  lvmio header run.lvm
  lvmio header run.lvm --json
  lvmio channels run.lvm
  lvmio dump run.lvm --channel Voltage --time
  lvmio dump run.lvm --segment 0 --format json
  lvmio header old.lvm --encoding cp1252
  cat run.lvm | lvmio header -
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``lvmio`` console script; returns the exit status.

    Errors print one short line to standard error and return 1; invalid arguments make
    argparse print its usage and exit with status 2. Redirected output is UTF-8.

    >>> main(["header", "no-such-file.lvm"])
    1
    """
    _utf8_when_redirected()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return dispatch(args, _load(args.path, args.encoding))
    except BrokenPipeError:
        _silence_stdout()
        return 0
    except (OSError, ValueError, KeyError, IndexError, LookupError) as exc:
        print(f"lvmio: error: {_message(exc)}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvmio",
        description="Inspect and export LabVIEW Measurement (.lvm) files.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvmio {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", help="path to a .lvm file, or - for standard input")
    common.add_argument(
        "--encoding", help="text encoding (default: UTF-8, else Windows-1252 as LabVIEW writes)"
    )
    subparsers = parser.add_subparsers(dest="command")
    header = subparsers.add_parser("header", parents=[common], help="show the file header fields")
    header.add_argument("--json", action="store_true", help="emit the header as JSON")
    subparsers.add_parser("channels", parents=[common], help="list the channels per segment")
    dump = subparsers.add_parser("dump", parents=[common], help="dump data as CSV or JSON")
    dump.add_argument("--channel", help="dump only this channel (default: all)")
    dump.add_argument("--segment", type=_index, default=0, help="segment index (default: 0)")
    dump.add_argument(
        "--format", choices=("csv", "json"), default="csv", help="output format (default: csv)"
    )
    dump.add_argument("--time", action="store_true", help="include the X (time) axis column")
    return parser


def _load(path: str, encoding: str | None) -> LvmFile:
    if path == "-":
        if sys.stdin is None:
            raise OSError("no standard input")
        return parse_lvm(decode(sys.stdin.buffer.read(), encoding))
    return read_lvm(path, encoding=encoding)


def _index(text: str) -> int:
    """A segment index; long or malformed text is refused without echoing it."""
    if len(text) > 18 or not text.lstrip("-").isdigit() or not text.isascii():
        raise argparse.ArgumentTypeError(f"not a segment number: {shorten(text, 20)}")
    return int(text)


def _utf8_when_redirected() -> None:
    """Redirected output is UTF-8, so every channel name can be written on any system."""
    stream = sys.stdout
    if stream is not None and hasattr(stream, "reconfigure") and not stream.isatty():
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def _silence_stdout() -> None:
    """After a closed pipe, point stdout at devnull so the exit flush stays quiet."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError, AttributeError):
        pass


def _message(exc: BaseException) -> str:
    if isinstance(exc, KeyError):
        name = exc.args[0] if exc.args else ""
        return f"no such channel: {shorten(str(name))}"
    if isinstance(exc, FileNotFoundError):
        return f"no such file: {shorten(str(exc.filename))}"
    if isinstance(exc, OSError) and exc.strerror:
        return f"{exc.strerror}: {shorten(str(exc.filename))}"
    text = str(exc)
    return text if len(text) <= 300 else text[:300] + "..."


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the lvmio command as a real process, importing the lvmio under test."""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
from importlib import metadata
from pathlib import Path

import lvmio

PACKAGE_ROOT = str(Path(lvmio.__file__).resolve().parent.parent)


def env() -> dict[str, str]:
    """The child imports the same lvmio as this test run, wherever that lives."""
    child = dict(os.environ)
    child["PYTHONPATH"] = PACKAGE_ROOT + os.pathsep + child.get("PYTHONPATH", "")
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    return child


def installed_from_a_wheel() -> bool:
    """Whether lvmio is imported from an installed distribution, not from a source tree."""
    try:
        dist = metadata.distribution("lvmio")
    except metadata.PackageNotFoundError:
        return False
    origin = Path(str(dist.locate_file("lvmio"))).resolve()
    return Path(lvmio.__file__).resolve().parent == origin


def cli_command() -> list[str]:
    """The installed console script when lvmio comes from a wheel, else ``python -m lvmio``.

    An installed lvmio must have a working console script: a missing or wrong one fails here
    instead of being replaced by ``python -m lvmio``.
    """
    scripts = Path(sysconfig.get_path("scripts"))
    for name in ("lvmio.exe", "lvmio"):
        script = scripts / name
        if script.exists():
            probe = subprocess.run(
                [str(script), "--version"], capture_output=True, text=True, env=env()
            )
            if probe.stdout.strip() == f"lvmio {lvmio.__version__}":
                return [str(script)]
    if installed_from_a_wheel():
        raise AssertionError(f"lvmio is installed but its console script in {scripts} is broken")
    return [sys.executable, "-m", "lvmio"]


def run(cli: list[str], *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([*cli, *args], input=stdin, capture_output=True, text=True, env=env())


def run_bytes(cli: list[str], *args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([*cli, *args], input=stdin, capture_output=True, env=env())

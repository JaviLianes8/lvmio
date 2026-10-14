"""Run the lvmio command as a real process, importing the lvmio under test."""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import lvmio

PACKAGE_ROOT = str(Path(lvmio.__file__).resolve().parent.parent)


def env() -> dict[str, str]:
    """The child imports the same lvmio as this test run, wherever that lives."""
    child = dict(os.environ)
    child["PYTHONPATH"] = PACKAGE_ROOT + os.pathsep + child.get("PYTHONPATH", "")
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    return child


def cli_command() -> list[str]:
    """The console script of this interpreter when it runs this lvmio, else ``-m lvmio``."""
    scripts = Path(sysconfig.get_path("scripts"))
    for name in ("lvmio.exe", "lvmio"):
        script = scripts / name
        if script.exists():
            probe = subprocess.run(
                [str(script), "--version"], capture_output=True, text=True, env=env()
            )
            if probe.stdout.strip() == f"lvmio {lvmio.__version__}":
                return [str(script)]
    return [sys.executable, "-m", "lvmio"]


def run(cli: list[str], *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([*cli, *args], input=stdin, capture_output=True, text=True, env=env())


def run_bytes(cli: list[str], *args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([*cli, *args], input=stdin, capture_output=True, env=env())

"""Shared fixtures."""

from __future__ import annotations

import pytest
from _clirun import cli_command


@pytest.fixture(scope="session")
def cli() -> list[str]:
    """The command that runs the lvmio under test."""
    return cli_command()

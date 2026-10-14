"""The documentation runs: doctests, README and GUIDE examples, links."""

from __future__ import annotations

import doctest
import importlib
import inspect
import re
from pathlib import Path

import pytest

import lvmio

ROOT = Path(__file__).resolve().parent.parent
MODULES = [
    "lvmio",
    "lvmio._check",
    "lvmio._cli",
    "lvmio._cli_output",
    "lvmio._errors",
    "lvmio._model",
    "lvmio._number",
    "lvmio._read",
    "lvmio._render",
    "lvmio._segment",
    "lvmio._write",
]
DOCS = [p for p in (ROOT / "README.md", ROOT / "GUIDE.md") if p.exists()]


@pytest.mark.parametrize("name", MODULES)
def test_module_doctests_pass(name: str) -> None:
    module = importlib.import_module(name)
    result = doctest.testmod(module, optionflags=doctest.ELLIPSIS)
    assert result.failed == 0


def test_every_module_is_listed() -> None:
    found = {f"lvmio.{p.stem}" for p in (Path(lvmio.__file__).parent).glob("_*.py")}
    found.discard("lvmio.__init__")
    found.discard("lvmio.__main__")
    assert found | {"lvmio"} == set(MODULES)


@pytest.mark.parametrize("name", lvmio.__all__)
def test_every_public_name_has_a_runnable_example(name: str) -> None:
    obj = getattr(lvmio, name)
    assert ">>>" in (inspect.getdoc(obj) or ""), name
    if inspect.isclass(obj) and name != "LvmError":
        for attr, member in vars(obj).items():
            if attr.startswith("_") or not callable(member):
                continue
            assert ">>>" in (inspect.getdoc(member) or ""), f"{name}.{attr}"


def _pycon_blocks(path: Path) -> list[str]:
    return re.findall(r"```pycon\n(.*?)```", path.read_text(encoding="utf-8"), re.S)


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_pycon_examples_run(path: Path) -> None:
    for block in _pycon_blocks(path):
        test = doctest.DocTestParser().get_doctest(block, {}, path.name, str(path), 0)
        runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
        runner.run(test)
        assert runner.failures == 0, block


def test_readme_has_examples() -> None:
    assert len(_pycon_blocks(ROOT / "README.md")) >= 2


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_links_are_absolute(path: Path) -> None:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        assert target.startswith("https://"), target


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_examples_import_only_public_names(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "lvmio._" not in text
    for names in re.findall(r"from lvmio import ([\w, ]+)", text):
        for name in names.split(","):
            assert name.strip() in lvmio.__all__


def test_readme_command_lines_are_real_subcommands() -> None:
    from lvmio._cli import _build_parser

    parser = _build_parser()
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    block = text.split("## Command line")[1].split("```")[1]
    for line in block.strip().splitlines():
        args = line.split("#")[0].split()
        if args and args[0] == "lvmio":
            parsed = parser.parse_args(args[1:])
            assert parsed.command in {"header", "channels", "dump"}

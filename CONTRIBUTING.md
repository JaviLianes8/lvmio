# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/lvmio/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests write only to temporary folders
  (`tmp_path`) and need no network.
- The fixtures in `tests/fixtures` are written by `python scripts/make_lvm_fixtures.py`;
  change the generator and rerun it rather than editing them. Do not commit `.lvm` files
  copied from elsewhere.
- The files in `tests/fixtures/labview2026` are what LabVIEW 2026 wrote and read on the
  maintainer's machine. `python scripts/capture_labview.py` recreates them (Windows,
  LabVIEW 2026 and pywin32 needed) and rewrites `manifest.json`; never edit them by hand.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.

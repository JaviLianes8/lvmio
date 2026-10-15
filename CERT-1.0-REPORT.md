# lvmio 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.1)
- [x] Baseline gates run on 0.2.1
- [x] Real LabVIEW 2026 captures (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.1 (items 8, 10, 13, 14), author run
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15), final run
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Scorecard

Filled in at the head of the pull request once the reviewer and the five lenses report.

## Baseline on 0.2.1 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 45 passed |
| `pytest --doctest-modules src` | no doctests at all |

Defects found in 0.2.1 against the LabVIEW captures:

- Samples were written with six fixed decimals: `1e-9` became `0.000000` (LabVIEW read it
  back as 0), `1e300` a 301-digit number. LabVIEW writes exponent notation outside 1e-4 to
  1e7. NaN was written as an empty cell and infinity as `inf`.
- `X_Columns` `Multi`, the layout LabVIEW's express VI worker writes when asked for an X
  column per channel, was misread: every `X_Value` column became a channel and the header
  cells were assigned to the wrong channels.
- A file a second LabVIEW session appended to (it repeats the whole file header) produced an
  extra empty segment.
- Cells were read with Python's `float`: `1_0` read as 10, which LabVIEW reads as 1.
- `read_lvm` decoded only UTF-8; LabVIEW writes text in the Windows code page (`é` as
  `0xE9`), so such files raised `UnicodeDecodeError`, which the command line did not catch.
- A file or segment header without its end marker silently gave fewer segments.
- The writer accepted names holding the separator or a line break, unknown separator
  names, booleans and strings as samples, and wrote files that read back differently.
- Error messages quoted whole cells.
- `lvmio dump` CSV had a blank line after every row on Windows, JSON output was invalid for
  infinities, and the end-to-end tests ran whatever `lvmio` was first on `PATH` (the 0.2.1
  release on this PC) instead of the code under test.

## Ground truth (item 7)

`tests/fixtures/labview2026/` holds what LabVIEW 2026 Community 26.3.1f1 wrote and read on
this PC on 2026-10-14 (Spanish regional settings, decimal comma). `scripts/capture_labview.py`
ran the Write To Measurement File express VI instance and its worker VI
(`ex_subFileWrite.vi`, which exposes the X column layout and append mode), fed through
LabVIEW's own `2D Dbl to DDT.vi`, and LabVIEW's Read From Measurement File instance with
`DDT to 2D Dbl.vi`, all through LabVIEW's ActiveX server. `manifest.json` records how each
file was made, its size and SHA-256; `.gitattributes` keeps the files byte for byte.

- Written by LabVIEW: the express VI default file, the three X column layouts, 400 seeded
  values from subnormals to the largest double (`numbers.lvm`, inputs in
  `numbers_input.json` as `float.hex`), NaN, infinities and signed zero, three appended
  segments with comments, a file appended by a second session (repeated file header), a
  Windows-1252 comment, and the period-on-a-comma-locale setting.
- Read by LabVIEW (`read_results.json`): every file above, five hand-written layouts,
  twenty single-cell spellings, and eight files written by lvmio 1.0.0.
- Findings: the number format rule matches all 400 seeded cells; every capture except two
  reads and writes back byte for byte; LabVIEW's reader reads every lvmio file with the
  written values; LabVIEW's reader takes the longest numeric prefix of a cell (`1_0` → 1,
  `0x10` → 0, `2.5V` → 2.5, `abc` → error 100) and truncates its own writer's periods in a
  comma file (`2.500000` → 2). lvmio refuses the first group and reads 2.5 for the last;
  the GUIDE lists every difference and `tests/test_labview_captures.py` pins them.
- Not capturable through ActiveX: channel names and units (the conversion VIs name channels
  `Untitled`), and `Delta_X` other than 1. Units and names come from lvmio's own files read
  by LabVIEW.
- Independent oracle: `lvm_read` 1.26 (`tests/test_crosscheck.py`) on the generated fixtures.

## API review (item 1)

Kept: `Channel`, `Segment`, `LvmFile`, `LvmError`, `parse_lvm`, `read_lvm`, `write_lvm` and
the `lvmio` command. Changed for 1.0.0 (all in CHANGELOG and the GUIDE upgrade section):
`format_lvm` added; `x_columns` and `encoding` arguments; `read_lvm(encoding=)`;
`Segment.comment`; `LvmFile.multi_headings` became a field read from the file; typed,
documented writer refusals (`TypeError`, `ValueError`) with nothing written on refusal;
`python -m lvmio` and `--encoding`.

## Author mutation rounds (item 18)

Each mutation was applied alone to a fresh clone of the pushed branch on a separate build
machine, the suite run with `-x`, no bytecode written (`-B`, `PYTHONDONTWRITEBYTECODE`,
`__pycache__` purged before each run), a 900 s limit per mutant, and the file restored; the
baseline was green before and after every round. The list grew with the code: number
format, reader, segment and split rules, writer checks, rendering, model and command line.

| Round | Head | Mutants | Killed at once | Survivors and outcome |
| --- | --- | --- | --- | --- |
| 1 | 9d7ce79 | 50 | 41 | 8 killed by new contracts in `tests/test_contract_edges.py` (39b24b8); M23 (comma decimal in a comma file) removed with its dead code |
| 2 | 27c680c | 68 | 66 | M04 (zero special case) equivalent, code removed as redundant; M60 (blank line message) killed by a new contract; both in 25d5db7 |
| 3 | bf6e04a | 89 | 87 | M69 (comment on a later row) and M80 (X cells of a Multi file) killed by new contracts in 2521431 |
| 4 | f327621 | 92 | 91 | M92 (a one-row write lending the next write its step) killed by a new contract in b922222 |
| 5 | 1d0436e | 100 | 99 | M80 had become equivalent once every X column is parsed while splitting segments; the redundant check was removed in the next commit. The list added the origin term of the split allowance, every Multi X column, padding after a split, codec messages, the fixed decimal context and the CSV X columns, all killed. Run in three parts on three workers at once |

Round 1 survivors and their contracts: Multi X cells from the first channel and Delta_X
decimals at low precision (`test_the_files_labview_read_back_are_still_what_lvmio_writes`),
closed pipe, shortened channel name in errors, `get` returning the first match, byte order
mark, a segment following rows without a blank line, standard input decoding (one test
each in `tests/test_contract_edges.py`).

## Packaging and end-to-end (items 8, 10, 14), author run

- `python -m build` and `twine check --strict`: both artifacts PASSED.
- Wheel: the twelve package modules, `py.typed`, LICENSE and metadata. Sdist: `src`, `tests`
  with the LabVIEW captures and their manifest, README, GUIDE, CHANGELOG, CONTRIBUTING,
  LICENSE, pyproject, the fixture generator and the `.gitignore` hatchling adds; no capture
  script, report or process notes.
- The wheel in a fresh venv on CPython 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8 and
  3.14.8 free-threaded, with the suite run from the extracted sdist with `src` removed (so
  it imports the installed wheel and drives its console script): exit 0 on all six.
- PyPI 0.2.1 installed, then upgraded in place to the 1.0.0 wheel: `1e-9` written as
  `0.000000` then `1.000000E-9`, infinity `inf` then `Inf`, `format_lvm` absent then present,
  console script reports `lvmio 1.0.0`.

## Independent QA lenses (item 19), rounds so far

Every lens was an independent reviewer that read the certification rules and CERT-1.0.md
first, worked in its own clone, ran things rather than reading, and reported back
privately. Findings were fixed, pinned by tests where they concern behaviour, and checked
again by a new reviewer with the same lens.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | dcceacf | FAIL | NumPy arrays and generators refused by the writer, redirected CLI output on non-cp1252 names, exit 2 undocumented, header line numbers, private module names, docstring and CHANGELOG gaps; fixed in 6b464e7 |
| a | 2 | a6942f0 | FAIL | generator data consumed by a first write, description blanks lost, CHANGELOG omissions, hints narrower than the docs, two inaccurate sentences; fixed in 1dac43c |
| a | 3 | 1dac43c | FAIL | a stale GUIDE bullet, lvmio's own files with a large X0 split at precision 17, padded short channels read back with NaN; fixed in fe27684 and 85faffb |
| a and d | 4 | 8e8e756 | PASS | API, typing of a client script, frozen objects, about 20 error cases and every example checked; wheel and sdist contents, the suite against the installed wheel on CPython 3.10 to 3.14, console script and `python -m lvmio` on the captures, upgrade from 0.2.1; minor: a CHANGELOG precision note, error order for a missing file with an unknown encoding, singular counts; fixed in 5eb5dd9 |
| b. Correctness and ground truth | 1 | 27c680c | FAIL | rounding of exact ties, comment escapes, undocumented reader differences; fixed in 21bb068 and 27c680c |
| b | 2 | ac8c4dc | FAIL | exponent ties at decimal exponents 11, 16, 17, near ties, the 1e-4 rewrite boundary, UTF-8 in LabVIEW; fixed in 554d3cc |
| b | 3 | 554d3cc | FAIL | Delta_X rounding and X cells, Delta_X floor unpinned, fixed-notation near ties; fixed in e99fb62 |
| b | 4 | e99fb62 | FAIL | LabVIEW's reader one ulp off on some cells, period cell in a comma file, wording; fixed in 5e65e0d |
| b | 5 | 5e65e0d | FAIL | X0 spelling, Samples and Channels counts, form feeds, a t0 sentence; fixed in bf121fe |
| b | 6 | bf121fe | FAIL | blank lines in headers, rows of empty cells, segment-header keys, spaces after a sign, BOM, unit shift; fixed in d11a62e and 3e58e77 |
| b | 7 | 3e58e77 | FAIL | one-header mode, unit V for files without units, per-channel dates, Description and Notes; fixed in 9968457 |
| b | 8 | 9968457 | FAIL | later-write comments and X origins in one-header files, Date/Time lines, X dimensions, X0 as a timestamp; fixed in 1dac43c |
| b | 9 | 1dac43c | FAIL | a negative X increment split every row, a later write that jumps forward or changes step was merged; fixed in c13bf36 |
| b | 10 | fe27684 | FAIL | the GUIDE misdescribed how LabVIEW reads per-channel Samples counts; corrected and pinned with two new LabVIEW reads in bf6e04a |
| b and c | 11 | 2521431 | FAIL | a 25 % step allowance on later writes, one-row writes merged, `0e400` X cells overflowing, odd Samples counts; fixed in f327621 |
| b and c | 12 | f327621 | FAIL | lvmio's own files splitting near X = 0 at precision 14 to 17, quadratic time on one-row-per-write logs, the caller's decimal context, later Multi X columns unchecked, padding after a split, two messages and wording; fixed in 730fceb and 5cddf3a |
| b and c | 13 | 730fceb | PASS | fixes confirmed by 10k round-trip files, 160k grammar files and 24k mutated fixtures, linear time to 160k rows; five minor items (CSV `--time` X column for Multi, escaped names in `channels`, three doc points) fixed in 4945f4a |
| c. Adversarial and robustness | 1 | 6b464e7 | FAIL | quadratic short rows, whitespace asymmetry, hostile decimal separator, Decimal overflow, sets as samples, lying subclasses; fixed in 21bb068 and 27c680c |
| c | 2 | e10090d | FAIL | headers without an end marker, closed stdout, dropped segment dates, long encoding names; fixed in 07fd565 |
| c | 3 | 07fd565 | FAIL | file header blank-line rule, encoding name echo, `undefined` codec; fixed in a6942f0 |
| c | 4 | 3e58e77 | PASS | 60k mutated texts, 20k mutated byte files, 60k writer and 60k reader grammar files, 120k comment round trips, 1,200 CLI runs, scaling ratios 2.4 to 4.6; optional items fixed in 6d97d31 |
| d. Packaging and real e2e | 1 | 27c680c | PASS | six interpreters green from the wheel, upgrade from 0.2.1 matches the CHANGELOG; a broken console script was not caught and the dev extra was public; fixed in ac8c4dc |
| e. Contract strength (blind mutations) | 1 | 27c680c | FAIL, then PASS with its contracts | 146 mutations, 114 killed, 3 equivalent, 29 needed contracts (tests/test_contract_more.py, e10090d), each confirmed by the reviewer to kill its mutant |
| e | 2 | a12dd19 | FAIL | 227 mutations, 186 killed, 3 equivalent, 38 needing contracts (one on code removed in b3c1119); the 37 contracts added in dec6e72 (`tests/test_contract_e2_read.py`, `tests/test_contract_e2_split.py`), each confirmed by the reviewer to kill its mutant |
| e | 3 | a7933d3 | FAIL | 337 mutations over all eleven modules, 297 killed, 8 equivalent (each explained: unreachable branches, `LookupError` subclasses, identical digits), 32 needing contracts; added in the next commit (`tests/test_contract_e3_lib.py`, `tests/test_contract_e3_cli.py`), each confirmed by the reviewer to fail on its mutant |
| e | 4 | 37e4f60 | FAIL | 329 mutations over every module, 311 killed, 4 equivalent (an unreachable branch, two `LookupError` subclasses, a cap no message reaches), 14 needing contracts, among them `channels` listing only the first channel; added in the next commit (`tests/test_contract_e4.py`), each confirmed to fail on its mutant |
| e | 5 | 7620bfe | FAIL | 327 mutations over every module on two machines (136 run on both, every verdict matched), 314 killed, 4 equivalent, 9 needing contracts (decoding offsets, the exact first line, a lone X column, X origin without an X column, a later write with an empty third X cell, refusal order, the path in CLI errors); added in the next commit (`tests/test_contract_e5.py`) |
| e | 6 | b4c4034 | FAIL | 338 mutations, 328 killed, 3 equivalent, 7 needing contracts (quoting of unprintable encoding names, any `\XX` escape, the default operator of a segment, refusal spellings, the CLI message cap, exact `X_Value` spelling, the third-row rule for a channel's own step); added in the next commit (`tests/test_contract_e6.py`) |
| e | 7 | bbf21d8 | PASS after contracts | bounded confirmation round: the seven round 6 survivors are killed by their contracts; a sweep of 40 new mutations on the code changed since the earlier reviews killed 31, 2 equivalent (the fixed decimal context's rounding and exponent limits, checked on about 400,000 doubles), 7 killed by the contracts added in the next commit (`tests/test_contract_e7.py`), each confirmed to fail on its mutant |

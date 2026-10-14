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

## Author mutation round (item 18)

Each mutation was applied alone to a fresh clone of the pushed branch on a separate build
machine, the suite run with `-x`, no bytecode written (`-B`,
`PYTHONDONTWRITEBYTECODE`, `__pycache__` purged before each run), a 900 s limit per
mutant, and the file restored; the baseline was green before and after. 50 mutations: 41
killed at once, 8 survived and were killed by new contracts in
`tests/test_contract_edges.py`, 1 removed with its code (M23 guarded a header form the
writer refuses and LabVIEW never produced).

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | fixed notation from 1e-5 | `_number.py` | killed | `test_labview_captures.py::test_rewriting_a_labview_file_gives_back_its_exact_bytes[numbers.lvm]` |
| M02 | fixed notation up to 1e8 | `_number.py` | killed | same, `numbers.lvm` |
| M03 | 1e7 itself in fixed notation | `_number.py` | killed | same, `numbers.lvm` |
| M04 | zero not special-cased | `_number.py` | killed | `test_docs.py::test_module_doctests_pass[lvmio._write]` |
| M05 | exponent padded to two digits | `_number.py` | killed | `test_docs.py::test_module_doctests_pass[lvmio._number]` |
| M06 | NaN spelled nan | `_number.py` | killed | `test_rewriting_a_labview_file_gives_back_its_exact_bytes[specials.lvm]` |
| M07 | negative infinity spelled -inf | `_number.py` | killed | `test_module_doctests_pass[lvmio._number]` |
| M08 | X0 with 15 decimals | `_number.py` | killed | `test_module_doctests_pass[lvmio._number]` |
| M09 | decimal comma not converted | `_number.py` | killed | `test_cli_edges.py::test_encoding_option_is_applied_and_checked` |
| M10 | grammar check skipped | `_number.py` | killed | `test_cli_edges.py::test_a_huge_bad_cell_is_not_echoed_back` |
| M11 | Infinity spelling unknown | `_number.py` | killed | `test_lvmio_reads_what_labview_reads[read/token_17.lvm]` |
| M12 | sign of special values dropped | `_number.py` | killed | `test_cli_edges.py::test_json_dump_stays_valid_json_with_infinities` |
| M13 | any Unicode blank stripped | `_number.py` | killed | `test_number.py::test_parse_number_refuses_everything_else[\xa07]` |
| M14 | two signs accepted on specials | `_number.py` | killed | `test_parse_number_refuses_everything_else[++inf]` |
| M15 | header cells not shifted for the X column | `_segment.py` | killed | `test_fixtures.py::test_short_tab_decimal_comma` |
| M16 | Comment column read as a channel | `_segment.py` | killed | `test_encoding_option_is_applied_and_checked` |
| M17 | X_Value columns read as channels | `_segment.py` | killed | `test_cli_edges.py::test_multi_x_columns_dump` |
| M18 | empty cell read as zero | `_segment.py` | killed | `test_contract.py::test_empty_fields_become_nan` |
| M19 | repeated file header parsed as a segment | `_read.py` | killed | `test_lvmio_reads_what_labview_reads[appended_runs.lvm]` |
| M20 | missing segment end marker tolerated | `_segment.py` | killed | `test_hostile.py::test_truncated_and_empty_files_are_refused[5]` |
| M21 | Latin-1 instead of Windows-1252 | `_read.py` | killed | `test_labview_writes_windows_1252_and_lvmio_reads_it` |
| M22 | Multi_Headings never read | `_read.py` | killed | `test_contract.py::test_lvmfile_iterates_segments_and_reports_multi_headings` |
| M23 | comma decimal in a comma file lost | `_read.py` | survived, code removed | the special case was dead for any file LabVIEW or lvmio writes |
| M24 | comma separator never detected | `_read.py` | killed | `test_contract.py::test_parse_lvm_matches_read_lvm_on_the_same_bytes` |
| M25 | no separator line after the file header | `_render.py` | killed | `test_rewriting_a_labview_file_gives_back_its_exact_bytes[comment_cp1252.lvm]` |
| M26 | Multi header width one short | `_render.py` | killed | same, `x_columns_multi.lvm` |
| M27 | Y_Unit_Label always written | `_render.py` | killed | same, `comment_cp1252.lvm` |
| M28 | Multi_Headings Yes for one segment | `_render.py` | killed | `test_lvmfile_iterates_segments_and_reports_multi_headings` |
| M29 | X values written in No files | `_render.py` | killed | same as M25, `express_default.lvm` |
| M30 | comment on every row | `_render.py` | killed | same as M25, `comment_cp1252.lvm` |
| M31 | Multi X cells from the first channel | `_render.py` | survived, then killed | new `test_contract_edges.py::test_the_files_labview_read_back_are_still_what_lvmio_writes` |
| M32 | Delta_X with 6 decimals whatever the precision | `_render.py` | survived, then killed | same new test (`lvmio_precision.lvm`) |
| M33 | bool accepted as a sample | `_check.py` | killed | `test_validation.py::test_bad_data_is_refused[data6-TypeError]` |
| M34 | reserved channel names accepted | `_check.py` | killed | `test_bad_data_is_refused[data17-ValueError]` |
| M35 | separator inside a field accepted | `_check.py` | killed | `test_bad_data_is_refused[data19-ValueError]` |
| M36 | comma as separator and decimal accepted | `_check.py` | killed | `test_bad_data_is_refused[data29-ValueError]` |
| M37 | precision up to 30 accepted | `_write.py` | killed | `test_bad_keywords_are_refused[kwargs1-ValueError]` |
| M38 | file opened before the data is checked | `_write.py` | killed | `test_bad_data_is_refused[text-TypeError]` |
| M39 | CSV rows end with CRLF again | `_cli_output.py` | killed | `test_multi_x_columns_dump` |
| M40 | infinity left as a float in JSON | `_cli_output.py` | killed | `test_json_dump_stays_valid_json_with_infinities` |
| M41 | closed pipe not handled | `_cli.py` | survived, then killed | new `test_a_closed_output_pipe_exits_zero_and_silently` (the first version wrote less than a pipe buffer) |
| M42 | channel name in the error not shortened | `_cli.py` | survived, then killed | new `test_a_huge_unknown_channel_name_is_not_echoed` |
| M43 | time axis one sample long | `_model.py` | killed | `test_json_dump_stays_valid_json_with_infinities` |
| M44 | get returns the last match | `_model.py` | survived, then killed | new `test_get_returns_the_first_of_two_channels_with_one_name` |
| M45 | comment cells joined without the separator | `_segment.py` | killed | `test_validation.py::test_the_comment_may_hold_the_separator_and_round_trips` |
| M46 | byte order mark kept | `_read.py` | survived, then killed | new `test_a_byte_order_mark_is_ignored` |
| M47 | messages quote the whole input | `_number.py` | killed | `test_a_huge_bad_cell_is_not_echoed_back` |
| M48 | segment rows run into the next segment header | `_segment.py` | survived, then killed | new `test_a_segment_may_follow_the_rows_without_a_blank_line` |
| M49 | stdin decoded with the default encoding | `_cli.py` | survived, then killed | new `test_standard_input_utf8_is_not_read_in_the_locale_encoding` |
| M50 | encoding option ignored for files | `_cli.py` | killed | `test_encoding_option_is_applied_and_checked` |

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

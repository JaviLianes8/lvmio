# Improvement round for lvmio

A ranked list of substantial improvements, scored against the `.lvm` fixtures of the
time and cross-checked with the `lvm_read` package as an oracle. Items marked DONE are
delivered in this round. Note added for 1.0.0: those fixtures turned out to be of unknown
origin and were replaced in 0.2.1 by generated files; files written by LabVIEW 2026 itself
arrived with 1.0.0 (`tests/fixtures/labview2026`).

## 1. Correct column handling for real `X_Columns=No` files (DONE, correctness)

The fixtures of the time with `X_Columns=No` (`short.lvm`, `comments_on_some_rows.lvm`,
then taken to be LabVIEW output) still have an `X_Value` column in the data header and a
leading empty X field on every data row. The old reader keyed the column offset
off the `X_Columns` header field, so it read channel 0 from the empty X column and
shifted every signal by one. The reader now derives the offset from the data
header itself (a leading `X_Value` token), which matches those files and `lvm_read`
for both `No` and `One` files.

## 2. Empty data fields become NaN, not dropped (DONE, correctness)

Real files leave trailing or whole channels empty (`with_empty_fields.lvm`:
unconnected `Untitled` channels, and rows with no comment). The old reader dropped
empty cells, which silently misaligned a channel against its own time axis. Empty
cells now parse to `float('nan')`, so every channel keeps one value per row and
lengths stay honest. This is exactly what `lvm_read` does, and the cross-check
test proves element-for-element agreement.

## 3. Frozen, typed result objects (DONE, API)

`Channel`, `Segment` and `LvmFile` are now frozen dataclasses: safe to pass around
and compare by value, no accidental mutation of a parsed result.

## 4. Time axis from X0 and Delta_X (DONE, API)

`Channel.time_axis()` returns `[x0, x0 + delta_x, ...]`, one value per sample, so
callers get the real X axis without recomputing it by hand.

## 5. Mapping-like and iterable access (DONE, API)

`Segment` supports `segment["Voltage"]`, `segment.get(name)`, `name in segment`,
`len(segment)`, `segment.names` and iteration over its channels. `LvmFile`
supports `len(lvm)` and iteration over its segments. Access by channel name is the
natural way to pull one signal out of a multi-channel capture.

## 6. Parse from text, not only from a path (DONE, API)

`parse_lvm(text)` parses an in-memory string; `read_lvm(path)` now delegates to it.
Useful for data pulled from a socket, an archive, or a test, and it powers the CLI
reading from standard input.

## 7. A real command line tool (DONE, CLI)

A `lvmio` console script (argparse, `[project.scripts]`) with subcommands:
`header` (metadata as text or JSON), `channels` (list channels per segment),
`dump` (one channel or all data as CSV or JSON, optionally with the time axis),
and `--version`. Errors go to stderr with exit code 1. `--help` carries runnable
examples.

## 8. Honest errors on malformed input (DONE, robustness)

`read_lvm` and `parse_lvm` raise `LvmError` (a `ValueError`) with a clear message
for files that are not LabVIEW Measurement text or that carry a non-numeric sample,
rather than failing with an opaque built-in error.

## 9. Scientific notation and decimal comma (already supported, now proven)

European LabVIEW writes `3,906250E-5` with a decimal comma. The reader already
handled the configurable decimal separator and exponent form; the committed
fixtures now lock that behaviour in with golden tests.

## Considered, intentionally out of scope this round

- `X_Columns=Multi` (one X column per channel). None of the genuine fixtures use
  it; it would need a per-channel X model and real sample files to validate.
- Absolute-time X axes as `datetime` objects. The per-channel `Date`/`Time` are
  captured as strings; turning them into timestamps needs a documented timezone
  policy and is deferred.
- Streaming / chunked reading for very large captures (the upstream `long.lvm`
  sample, not committed here, is several MB). The current reader loads the whole
  file, which is fine for typical use.

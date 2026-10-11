# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `write_lvm` serialises channels to a spec-faithful `.lvm` file, filling the
  writer gap that existing readers leave open.
- `read_lvm` parses the file header and data segments back into typed objects.
- `Channel`, `Segment` and `LvmFile` model the format; `LvmError` reports invalid
  input.
- Supports Tab and Comma separators, a configurable decimal separator, multiple
  segments, and `X_Columns` set to `One` or `No`.

# Python Port of `dam`

This document describes the Python + Click port of `dam`, how to run it locally, and the current status of the migration from the original Node proof of concept.

## Current state

The Python CLI is implemented under [src/dam](/Users/jasonb/Self/projects/dam/src/dam) and is invoked through the repo-local launcher [dam](/Users/jasonb/Self/projects/dam/dam).

Implemented commands:

- `what-can PHOTO_DIR`
- `ingest PHOTO_DIR`
- `apply-copyright PHOTO_DIR`
- `apply-rotation PHOTO_DIR`
- `sync`
- `cleanup PHOTO_DIR`
- `compare SOURCE_DIR TARGET_DIR`
- `rm-rejected`

Current behavior:

- The command names and overall workflow are intended to match the original Node CLI.
- Marker files are preserved: `.copyright`, `.rotate`, `.ingest`, `.clean`.
- Configuration still lives in `~/.dam/config.json`.
- `~/.dam/exiftool.conf` is created automatically on first run if missing.
- `rm-rejected` is exposed but still intentionally unimplemented.

## Runtime requirements

Python requirements:

- Python `3.9+`

External tools:

- `exiftool` is required for `apply-copyright`, `ingest`, and `compare`
- `exiftran` is required for `apply-rotation`

The Python launcher does not replace those tools. They still need to be available on your `PATH`.

## Running the CLI

The simplest way to run the Python port is through the repo-local launcher:

```bash
./dam --help
```

The launcher will:

- create `.venv` if needed
- ensure `click` is installed in that virtualenv
- run the CLI from the local `src/` tree

Example usage:

```bash
./dam what-can /path/to/photo-dir
./dam apply-copyright /path/to/photo-dir --no-dry
./dam ingest /path/to/photo-dir --no-dry
./dam sync --no-dry
```

## Virtualenv notes

You do not need to activate the virtualenv just to use the CLI. `./dam` is designed to bootstrap itself.

If you do activate `.venv` manually, prefer running Python tools through `python -m ...` so the interpreter and the tool always match.

Good:

```bash
source .venv/bin/activate
python -m pytest -q
```

For `fish`:

```fish
source .venv/bin/activate.fish
python -m pytest -q
```

Less reliable:

```bash
pytest
```

Reason: your shell may resolve `pytest` from Homebrew or another global install even while `python` resolves to `.venv/bin/python`.

If you want the venv-local test runner explicitly:

```bash
.venv/bin/pytest -q
```

## Running tests

From the repo root:

```bash
python -m pytest -q
```

or, without activation:

```bash
PYTHONPATH=src ./.venv/bin/pytest -q
```

Current test coverage includes:

- config loading and default generation
- Click CLI command registration
- command behavior with mocked external tools
- sync filesystem behavior
- real image asset tests under [tests/assets](/Users/jasonb/Self/projects/dam/tests/assets)

Real asset tests currently exercise `exiftool`-backed behavior when `exiftool` is installed.

## Project layout

Relevant files:

- [dam](/Users/jasonb/Self/projects/dam/dam): bootstrap launcher
- [pyproject.toml](/Users/jasonb/Self/projects/dam/pyproject.toml): Python package metadata
- [src/dam/cli.py](/Users/jasonb/Self/projects/dam/src/dam/cli.py): Click entrypoint
- [src/dam/config.py](/Users/jasonb/Self/projects/dam/src/dam/config.py): config defaults and bootstrap
- [src/dam/external.py](/Users/jasonb/Self/projects/dam/src/dam/external.py): subprocess wrappers for external tools
- [src/dam/commands](/Users/jasonb/Self/projects/dam/src/dam/commands): command implementations
- [tests](/Users/jasonb/Self/projects/dam/tests): test suite

## Conversion status

Converted to Python:

- CLI entrypoint
- config loading and `~/.dam` bootstrap
- `what-can`
- `apply-copyright`
- `apply-rotation`
- `ingest`
- `sync`
- `cleanup`
- `compare`
- test suite for both mocked behavior and real photo assets

Not yet fully converted or finalized:

- `rm-rejected` remains a placeholder
- README still primarily documents the original Node PoC
- packaging/install flow is partially migrated, but the most reliable local workflow today is the repo launcher plus `src/` execution

## Known gaps

- `apply-rotation` still depends on `exiftran`, and there is no live integration test for it on machines where `exiftran` is missing.
- The launcher bootstraps only what it needs to run the CLI cleanly. It is not yet a polished full installer for all developer tooling.
- The original Node code is still present in [lib](/Users/jasonb/Self/projects/dam/lib) for reference during the migration.

## Recommended workflow

For normal usage:

```bash
./dam --help
```

For development and testing:

```bash
source .venv/bin/activate
python -m pytest -q
```

For `fish`:

```fish
source .venv/bin/activate.fish
python -m pytest -q
```

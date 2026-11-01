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

## Safe sync on macOS/APFS

`sync` supports macOS/APFS only. Both configured user directories must already
exist and must not overlap. Stop digiKam, git-annex operations, other sync runs,
and other writers before syncing. Concurrent writers are not supported.

Images (`.jpg`, `.jpeg`, `.heic`, case-insensitive) flow from staging to digiKam.
Their resolved originals must already have no POSIX write bits; locked annex
image symlinks are supported when their objects are available. Sync never changes
original image contents or permissions. A read-only mode is not protection against
the file owner deliberately changing permissions.

New target images use the macOS `clonefile()` system call and mode `0600`.
Source and destination must support cloning on the same filesystem/volume.
There is no hard-link, symlink, or full-copy fallback. Clones have independent
permissions and contents; later writes may require additional disk space.
Existing shared target hard links and symlinks to the corresponding original are
replaced atomically with writable clones. Independent target edits are retained.
Sync cannot repair originals previously modified through old hard links. If such
an original is writable, sync refuses it rather than changing shared permissions.

XMP sidecars flow from digiKam back to staging. Ordinary sidecars are copied via
a temporary file and atomically replaced; unchanged contents are skipped.
Existing destination modes are retained, and new sidecars use `0600`. XMP
symlinks and multiply hard-linked staging XMP files are rejected. Annex-managed
sidecars require a separate workflow; this command does not modify annex objects.
The staging tree must permit these sidecar updates even though images are read-only.

Neither direction prunes files. Unmatched images and sidecars are retained.
Unavailable annex objects, missing roots, scan errors, directory symlinks, and
unsafe destination paths fail validation before any planned writes. Clone or
metadata execution errors stop the run, preserving the prior destination for the
failed publication. Earlier successful updates remain: atomicity is per file,
not per run. Temporary working files are cleaned on handled failures.

Existing flags and defaults still apply:

```bash
./dam sync                         # dry run, both directions
./dam sync --file-sync             # dry run, images only
./dam sync --meta-sync --no-dry     # apply sidecar updates only
./dam sync --no-dry                # apply both directions
```

Dry runs validate and report actions without creating files, directories, or
probes, or changing permissions. They cannot verify actual clone support or
effective destination writability. Run `python -m pytest -q` on macOS/APFS to
exercise real cloning, in-place write isolation, link migration, retention, and
injected failure handling. Real clone checks must pass before deployment.

from __future__ import annotations

from pathlib import Path

import click

from dam.external import log_message
from dam.paths import iter_files, marker_exists, require_directory, touch


def cleanup(photo_dir: Path, *, dry: bool) -> None:
    try:
        require_directory(photo_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc

    if not marker_exists(photo_dir, "ingest"):
        raise click.ClickException("Files must have been ingested.")

    files = [path for path in iter_files(photo_dir) if _cleanup_candidate(path)]
    for file_path in files:
        log_message(f"Unlinking {file_path.name}", dry=dry)
        if not dry and file_path.exists():
            file_path.unlink()

    if not dry:
        touch(photo_dir / ".clean")


def _cleanup_candidate(path: Path) -> bool:
    return path.name.endswith("_original") or path.name.endswith("~")

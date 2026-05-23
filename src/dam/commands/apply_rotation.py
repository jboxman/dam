from __future__ import annotations

from pathlib import Path

import click

from dam.external import log_message, run_exiftran
from dam.paths import iter_files, require_directory, touch


def apply_rotation(photo_dir: Path, *, dry: bool) -> None:
    try:
        require_directory(photo_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc

    files = [path for path in iter_files(photo_dir) if path.suffix.lower() == ".jpg"]
    success = True
    for file_path in files:
        if dry:
            run_exiftran(file_path, dry=True, execute=False)
            continue
        run_exiftran(file_path)
        log_message(f"Trying to rotate {file_path.name}")

    if not dry and success:
        touch(photo_dir / ".rotate")

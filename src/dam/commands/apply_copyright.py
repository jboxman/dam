from __future__ import annotations

import re
from pathlib import Path

import click

from dam.config import DamConfig
from dam.external import log_message, run_exiftool
from dam.paths import require_directory, touch


MEDIA_TYPES = ["jpg", "nef", "heic", "mov"]


def apply_copyright(config: DamConfig, photo_dir: Path, *, dry: bool) -> None:
    args_file = config.copyright_args_for_user()
    if not args_file.exists():
        raise click.ClickException(f"Cannot open exiftool args file: {args_file}")
    try:
        require_directory(photo_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc

    result = run_exiftool(
        path=photo_dir,
        file_types=MEDIA_TYPES,
        extra_args=["-@", str(args_file)],
        dry=dry,
        execute=not dry,
    )
    if dry:
        return

    for line in result.stdout_lines:
        log_message(line.strip())
    if any(re.search(r"\d+ image", line) for line in result.stdout_lines):
        touch(photo_dir / ".copyright")

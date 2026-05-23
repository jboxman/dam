from __future__ import annotations

import re
from pathlib import Path

import click

from dam.config import DamConfig, exiftool_config_file
from dam.external import log_message, run_exiftool
from dam.paths import marker_exists, require_directory, touch


MEDIA_TYPES = ["jpg", "nef", "heic", "mov"]


def ingest(config: DamConfig, photo_dir: Path, *, dry: bool) -> None:
    if not marker_exists(photo_dir, "copyright"):
        raise click.ClickException("Files must have attribution applied.")

    tool_config = exiftool_config_file()
    if not tool_config.exists():
        raise click.ClickException(f"{tool_config} does not exist!")

    try:
        require_directory(photo_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc

    target = "TestName" if dry else "FileName"
    staging_prefix = config.staging_user_dir / "%Y" / "%m" / "%d"

    is_apple = (photo_dir / ".osxphotos_export.db").exists()
    if is_apple:
        rename_args = [
            f"-{target}<${{CreateDate}}/${{filename;s/\\.[^.]*$//}}.%le",
            "-d",
            str(staging_prefix),
        ]
        expr = []
    else:
        rename_args = [
            f"-{target}<${{CreateDate}}${{MySequenceNum}}.%le",
            "-d",
            str(staging_prefix / "%Y%m%d-%H%M%S"),
        ]
        expr = ["defined $CreateDate"]

    result = run_exiftool(
        path=photo_dir,
        exiftool_config=tool_config,
        expr=expr,
        file_types=MEDIA_TYPES,
        extra_args=rename_args,
        dry=dry,
        execute=True,
    )

    if dry:
        matched = [line for line in result.stdout_lines if "-->" in line]
        for line in matched:
            log_message(line, dry=True)
        log_message(f"Files matched: {len(matched)}", dry=True)
        return

    for line in result.stdout_lines:
        log_message(line.strip())
    if any(re.search(r"\d+ image", line) for line in result.stdout_lines):
        touch(photo_dir / ".ingest")
    log_message("Enter `git annex add` to add the files to the annex.")

from __future__ import annotations

from pathlib import Path
from typing import Dict

import click

from dam.external import log_message, run_exiftool
from dam.paths import require_directory


def compare(source_dir: Path, target_dir: Path) -> None:
    for path in (source_dir, target_dir):
        try:
            require_directory(path)
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise click.ClickException(str(exc)) from exc

    common_args = [
        "-r",
        "-d",
        "%Y%m%d%H%M%S",
        "-p",
        "${Directory}^${FileName}^${DateTimeOriginal}${SubsecTimeOriginal}-${DirectoryNumber}-${FileNumber}",
    ]

    source_files = _run_compare_scan(source_dir, common_args)
    log_message(f"{source_dir}: {len(source_files)} files")
    target_files = _run_compare_scan(target_dir, common_args)
    log_message(f"{target_dir}: {len(target_files)} files")

    for key in sorted(source_files):
        if key not in target_files:
            log_message(f"Missing {source_files[key]['path']}")


def _run_compare_scan(base_dir: Path, common_args: list[str]) -> Dict[str, dict]:
    result = run_exiftool(
        path=base_dir,
        file_types=["jpg"],
        extra_args=common_args,
        dry=False,
        execute=True,
        check=True,
    )
    payload: Dict[str, dict] = {}
    for line in result.stdout_lines:
        payload.update(_by_key(line))
    return payload


def _by_key(value: str) -> Dict[str, dict]:
    dirname, filename, stamp = value.split("^")
    return {
        stamp: {
            "filename": filename,
            "dirname": dirname,
            "path": str(Path(dirname) / filename),
        }
    }

from __future__ import annotations

import os
import shutil
from pathlib import Path

import click

from dam.config import DamConfig
from dam.external import log_message
from dam.paths import iter_files, relative_map


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".heic"}


def sync(config: DamConfig, *, dry: bool, file_sync: bool, meta_sync: bool) -> None:
    source_root = config.staging_user_dir
    target_root = config.digikam_user_dir
    do_file_sync = file_sync
    do_meta_sync = meta_sync
    if not do_file_sync and not do_meta_sync:
        do_file_sync = True
        do_meta_sync = True

    if not dry:
        target_root.mkdir(parents=True, exist_ok=True)

    if do_file_sync:
        _file_sync(source_root, target_root, dry=dry)
    if do_meta_sync:
        _meta_sync(source_root, target_root, dry=dry)


def _file_sync(source_root: Path, target_root: Path, *, dry: bool) -> None:
    source_files = relative_map(
        [path for path in iter_files(source_root) if path.suffix.lower() in IMAGE_SUFFIXES],
        source_root,
    )
    target_files = relative_map(
        [path for path in iter_files(target_root) if path.suffix.lower() in IMAGE_SUFFIXES],
        target_root,
    )

    for relative, source_file in source_files.items():
        create_link(source_file, target_root / relative, dry=dry)

    for relative, target_file in target_files.items():
        if relative not in source_files and target_file.exists():
            log_message(f"Unlink: {target_file}", dry=dry)
            if not dry:
                target_file.unlink()


def _meta_sync(source_root: Path, target_root: Path, *, dry: bool) -> None:
    source_files = relative_map(
        [path for path in iter_files(target_root) if path.suffix.lower() == ".xmp"],
        target_root,
    )
    target_files = relative_map(
        [path for path in iter_files(source_root) if path.suffix.lower() == ".xmp"],
        source_root,
    )

    for relative, source_file in source_files.items():
        destination = source_root / relative
        log_message(
            f"Sync: {str(destination).replace(str(source_root), '<digikamDir>/...')}",
            dry=dry,
        )
        if not dry:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_file, destination)

    for relative, target_file in target_files.items():
        if relative not in source_files and target_file.exists():
            log_message(
                f"Unlink: {str(target_file).replace(str(source_root), '<photoDir>/...')}",
                dry=dry,
            )
            if not dry:
                target_file.unlink()


def create_link(source_file: Path, destination_file: Path, *, dry: bool) -> None:
    if destination_file.exists():
        return

    log_message(f"Create: {destination_file}", dry=dry)
    if dry:
        return

    destination_file.parent.mkdir(parents=True, exist_ok=True)
    source_real = source_file.resolve()
    os.link(source_real, destination_file)

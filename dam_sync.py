#!/usr/bin/env python3
import json
import os
import re
import shutil
import sys
from pathlib import Path

import click


def log(msg_type, message):
    click.echo(f"[{msg_type.upper()}] {message}")


def dry_log(message):
    log("dry", message)


def run_log(message):
    log("run", message)


def load_config():
    default_user = os.environ.get("USER", "")
    default_user_dir = os.environ.get("HOME", "")
    config_dir = Path(default_user_dir) / ".dam"
    config_file = config_dir / "config.json"

    default_config = {
        "defaultUser": default_user,
        "stagingDir": str(Path(default_user_dir) / "Self/repos/photos/photographers"),
        "digikamDir": str(Path(default_user_dir) / "Self/repos/photos-dk/photographers"),
        "photographers": {
            default_user: {
                "copyrightArgs": str(config_dir / f"{default_user}-copyright.conf")
            }
        },
    }

    config = {}
    try:
        config = json.loads(config_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}

    merged = {**default_config, **config}
    return merged


def list_files(root, include_regex):
    files = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if include_regex.search(filename):
                files.append(os.path.join(dirpath, filename))
    return files


def ensure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def create_link(src_file, dst_file, dry):
    if os.path.exists(dst_file):
        return

    msg = f"Create: {dst_file}"
    dry_log(msg) if dry else run_log(msg)

    if dry:
        return

    ensure_parent_dir(dst_file)
    src_file_real = os.path.realpath(src_file)
    try:
        os.link(src_file_real, dst_file)
    except OSError as exc:
        click.echo(exc, err=True)
        sys.exit(1)


def file_sync(photo_dir, target_dir, dry=True):
    include_regex = re.compile(r"\.(jpg|jpeg|heic)$", re.IGNORECASE)

    try:
        source_files = list_files(photo_dir, include_regex)
    except OSError as exc:
        click.echo(exc, err=True)
        sys.exit(1)

    source_set = {os.path.normpath(path) for path in source_files}

    try:
        target_files = list_files(target_dir, include_regex)
    except OSError as exc:
        click.echo(exc, err=True)
        sys.exit(1)

    for src_file in source_files:
        rel_path = os.path.relpath(src_file, photo_dir)
        dst_file = os.path.join(target_dir, rel_path)
        create_link(src_file, dst_file, dry)

    for target_file in target_files:
        rel_path = os.path.relpath(target_file, target_dir)
        source_equivalent = os.path.normpath(os.path.join(photo_dir, rel_path))
        if source_equivalent in source_set:
            continue
        if not os.path.exists(target_file):
            continue

        msg = f"Unlink: {target_file}"
        dry_log(msg) if dry else run_log(msg)

        if not dry:
            os.unlink(target_file)


def meta_sync(photo_dir, target_dir, dry=True):
    include_regex = re.compile(r"\.xmp$", re.IGNORECASE)

    try:
        source_files = list_files(target_dir, include_regex)
    except OSError as exc:
        click.echo(exc, err=True)
        sys.exit(1)

    try:
        target_files = list_files(photo_dir, include_regex)
    except OSError as exc:
        click.echo(exc, err=True)
        sys.exit(1)

    source_set = {os.path.normpath(path) for path in source_files}

    for file_path in source_files:
        rel_path = os.path.relpath(file_path, target_dir)
        dest_path = os.path.join(photo_dir, rel_path)

        msg = f"Sync: {dest_path.replace(photo_dir, '<digikamDir>/...')}"
        dry_log(msg) if dry else run_log(msg)

        if not dry:
            ensure_parent_dir(dest_path)
            try:
                shutil.copyfile(file_path, dest_path)
            except OSError as exc:
                click.echo(exc, err=True)
                sys.exit(1)

    for target_file in target_files:
        rel_path = os.path.relpath(target_file, photo_dir)
        source_equivalent = os.path.normpath(os.path.join(target_dir, rel_path))
        if source_equivalent in source_set:
            continue
        if not os.path.exists(target_file):
            continue

        msg = f"Unlink: {target_file.replace(photo_dir, '<photoDir>/...')}"
        dry_log(msg) if dry else run_log(msg)

        if not dry:
            os.unlink(target_file)


@click.command()
@click.option("--dry/--no-dry", default=True, help="Perform action")
@click.option(
    "--file-sync",
    "file_sync_flag",
    is_flag=True,
    help="Sync (hardlink) git-annex objects to digiKam working directory",
)
@click.option(
    "--meta-sync",
    "meta_sync_flag",
    is_flag=True,
    help="Sync (copy) .XMP metadata files to photos directory",
)
def sync(dry, file_sync_flag, meta_sync_flag):
    config = load_config()
    photo_dir = os.path.join(config["stagingDir"], config["defaultUser"])
    target_dir = os.path.join(config["digikamDir"], config["defaultUser"])

    do_file_sync = file_sync_flag
    do_meta_sync = meta_sync_flag
    if not do_file_sync and not do_meta_sync:
        do_file_sync = True
        do_meta_sync = True

    if not dry:
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as exc:
            click.echo(exc, err=True)
            sys.exit(1)

    if do_file_sync:
        file_sync(photo_dir, target_dir, dry=dry)
    if do_meta_sync:
        meta_sync(photo_dir, target_dir, dry=dry)


if __name__ == "__main__":
    sync()
